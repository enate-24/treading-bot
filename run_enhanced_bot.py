"""
Enhanced HFT Trading Bot with improved accuracy.
"""
import MetaTrader5 as mt5
import logging
import os
import time
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional
import signal
import sys
import asyncio

from dotenv import load_dotenv

# Minimum bars of history before signals are trusted
MIN_BARS_WARMUP = 50
# Halt new orders after this many consecutive failures (circuit breaker)
CIRCUIT_BREAKER_THRESHOLD = 10
RECONNECT_DELAY = 30
MAX_RECONNECT_ATTEMPTS = 5

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('metatrader_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def _safe_float(value, default=None):
    """Coerce broker-supplied numbers to float, falling back on bad values."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

# Import bot components
from trading_bot.connectors.metatrader_connector import MetaTraderConnector
from trading_bot.signal_generator import SignalGenerator
from trading_bot.strategies.enhanced_hft_strategy import EnhancedHFTStrategy
from trading_bot.session_manager import SessionManager
from trading_bot.performance_monitor import PerformanceMonitor
from trading_bot.risk_manager import RiskManager
from trading_bot.portfolio_adapter import MetaTraderPortfolioAdapter
from trading_bot.models.core import (
    MarketData, OHLCV, TradingSignal, ExecutedTrade, OrderRequest,
)
from trading_bot.models.enums import SignalDirection, OrderSide, OrderType, TimeInForce
from trading_bot.utils.indicators import (
    calculate_ema, calculate_rsi, calculate_macd,
    calculate_adx, calculate_atr, calculate_stochastic,
    calculate_cci, calculate_bollinger_bands,
)

class EnhancedBot:
    """Enhanced trading bot with improved accuracy."""
    
    def __init__(self, config_path: str = "config/metatrader_config_enhanced.json"):
        """Initialize the enhanced bot."""
        logger.info("=" * 60)
        logger.info("Initializing Enhanced HFT Bot")
        logger.info("=" * 60)
        
        # Load configuration directly
        import json
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
        
        # Convert to object for easy access
        from types import SimpleNamespace
        self.config = json.loads(json.dumps(config_dict), object_hook=lambda d: SimpleNamespace(**d))
        
        logger.info(f"[OK] Configuration loaded from {config_path}")
        
        # Load credentials from environment variables (Bug 7 fix)
        load_dotenv()
        try:
            mt5_account = int(os.environ["MT5_ACCOUNT"])
            mt5_password = os.environ["MT5_PASSWORD"]
            mt5_server = os.environ["MT5_SERVER"]
        except KeyError as e:
            raise EnvironmentError(
                f"Missing required environment variable: {e}. "
                "Set MT5_ACCOUNT, MT5_PASSWORD, and MT5_SERVER in your .env file or environment."
            )
        
        # Initialize components
        self.mt_connector = MetaTraderConnector(
            account=mt5_account,
            password=mt5_password,
            server=mt5_server,
            mt_version=config_dict['metatrader'].get('version', 5)
        )
        self.strategy_params = config_dict.get('strategy_parameters', {}).get('enhanced_hft', {})
        # One strategy + signal generator per (symbol, timeframe). Sharing a
        # single instance lets indicator/state buffers from EURUSD, JPY pairs
        # and XAUUSD contaminate each other and corrupt every signal.
        self.signal_generators: Dict[tuple, SignalGenerator] = {}
        self.session_manager = SessionManager(config_dict)
        self.performance_monitor = PerformanceMonitor(risk_free_rate=0.02)

        # Live risk controls: portfolio state comes from the broker so daily
        # loss, drawdown, correlation and emergency-stop checks use real
        # account figures.  close_position_fn lets the manager flatten a
        # position when its stop/take-profit is breached programmatically.
        risk_cfg = config_dict.get('risk_management', {})
        trading_cfg = config_dict.get('trading', {})
        self.portfolio = MetaTraderPortfolioAdapter(self.mt_connector)
        self.risk_manager = RiskManager(
            self.portfolio,
            {
                'max_risk_per_trade': risk_cfg.get('risk_per_trade', 0.01),
                'max_portfolio_drawdown': risk_cfg.get(
                    'max_portfolio_drawdown', trading_cfg.get('max_drawdown', 0.10)
                ),
                'daily_loss_limit': risk_cfg.get('daily_loss_limit', 0.05),
                'max_position_correlation': risk_cfg.get('max_position_correlation', 0.5),
                'emergency_stop_drawdown': risk_cfg.get('emergency_stop_drawdown', 0.15),
                'leverage': risk_cfg.get('leverage', 1),
            },
            close_position_fn=self.mt_connector.close_position,
        )
        
        # Trading state
        self.running = False
        self.open_positions: Dict[str, dict] = {}
        self.position_counter: Dict[str, int] = {}
        self.signal_count = 0
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        self._consecutive_failures = 0  # circuit breaker

        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        logger.info("[OK] Enhanced HFT Strategy loaded")
        logger.info("[OK] Multi-layer signal analysis enabled")
        logger.info("[OK] Dynamic risk management active")

    # ------------------------------------------------------------------
    # Broker position sync
    # ------------------------------------------------------------------

    def _sync_positions_from_broker(self) -> None:
        """Populate open_positions from any already-open MT5 positions on startup."""
        try:
            positions = self.mt_connector.get_positions()
            if not positions:
                logger.info("[OK] No existing positions on broker")
                return

            symbols = list(self.config.trading.symbols)
            for pos in positions:
                symbol = pos['symbol']
                if symbol not in symbols:
                    continue
                key = str(pos['ticket'])
                self.open_positions[key] = {
                    'symbol': symbol,
                    'order_id': pos['ticket'],
                    'direction': SignalDirection.BUY if pos['type'] == 'BUY' else SignalDirection.SELL,
                    'volume': pos['volume'],
                    'entry_price': pos['price_open'],
                    'sl': pos['sl'],
                    'tp': pos['tp'],
                    'timestamp': datetime.now(),
                    'confidence': 0.0,
                    'synced_from_broker': True,
                }
                if symbol not in self.position_counter:
                    self.position_counter[symbol] = 0
                self.position_counter[symbol] += 1
                logger.info(f"[SYNC] Loaded existing {pos['type']} {symbol} ticket={pos['ticket']}")

            logger.info(f"[OK] Synced {len(self.open_positions)} position(s) from broker")
        except Exception as e:
            logger.error(f"Error syncing positions: {e}")
    
    def _run_async(self, result):
        """Run an async coroutine from synchronous code.

        Non-coroutine values are returned unchanged so callers (and tests)
        that provide an already-resolved value keep working.
        """
        if not asyncio.iscoroutine(result):
            return result
        coro = result
        try:
            try:
                asyncio.get_running_loop()
                # Already inside a running loop — run in a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, coro)
                    return future.result()
            except RuntimeError:
                # No running loop — safe to create one
                return asyncio.run(coro)
        except Exception as e:
            logger.error(f"Error running async call: {e}")
            return None

    def _get_account_info_sync(self):
        """Synchronous wrapper for the async get_account_info coroutine."""
        return self._run_async(self.mt_connector.get_account_info())

    def _get_market_data_sync(self, symbol: str, timeframe: str, bars: int = 200):
        """Synchronous wrapper for the async get_market_data coroutine."""
        return self._run_async(self.mt_connector.get_market_data(symbol, timeframe, bars=bars))

    def calculate_position_size(self, symbol: str, signal) -> float:
        """Calculate dynamic position size based on confidence and volatility."""
        account_info = self._get_account_info_sync()
        if not account_info:
            return 0.01

        balance = account_info['balance']
        risk_per_trade = self.config.risk_management.risk_per_trade

        # Adjust risk based on signal confidence
        confidence_multiplier = signal.confidence
        adjusted_risk = risk_per_trade * confidence_multiplier

        # Adjust for volatility
        volatility = signal.metadata.get('volatility', 0.0001)
        if volatility > 0.0002:
            adjusted_risk *= 0.7
        elif volatility < 0.00005:
            adjusted_risk *= 1.2

        risk_amount = balance * adjusted_risk
        stop_loss_pct = signal.metadata.get('stop_loss', 0.0002)

        sym_info = mt5.symbol_info(symbol)
        if sym_info is None:
            logger.warning(f"Cannot get symbol info for {symbol}, using min lot")
            return 0.01

        # Use ask for BUY, bid for SELL as reference price
        if signal.direction == SignalDirection.BUY:
            ref_price = _safe_float(getattr(sym_info, 'ask', None))
        else:
            ref_price = _safe_float(getattr(sym_info, 'bid', None))

        point = _safe_float(getattr(sym_info, 'point', 0.0), 0.0)
        contract = _safe_float(getattr(sym_info, 'trade_contract_size', 0.0), 0.0)

        # Risk is measured in price units: loss per lot = stop distance * contract.
        # This keeps sizing correct across FX, JPY pairs and metals, where a
        # fixed pip/point value would be wrong by orders of magnitude.
        if ref_price and ref_price > 0:
            stop_distance = ref_price * stop_loss_pct
        else:
            stop_distance = stop_loss_pct  # price unavailable; assume unit price

        min_lot  = _safe_float(getattr(sym_info, 'volume_min', 0.01), 0.01)
        max_lot  = min(_safe_float(getattr(sym_info, 'volume_max', 100.0), 100.0), 0.10)
        lot_step = _safe_float(getattr(sym_info, 'volume_step', 0.01), 0.01)

        if stop_distance <= 0 or contract <= 0:
            return min_lot

        lot_size = risk_amount / (stop_distance * contract)

        if lot_step > 0:
            lot_size = round(round(lot_size / lot_step) * lot_step, 2)

        return max(min_lot, min(lot_size, max_lot))
    
    def _get_signal_generator(self, symbol: str, timeframe: str) -> SignalGenerator:
        """Return the isolated signal generator for one symbol/timeframe pair."""
        key = (symbol, timeframe)
        generator = self.signal_generators.get(key)
        if generator is None:
            strategy = EnhancedHFTStrategy(self.strategy_params)
            generator = SignalGenerator()
            generator.set_strategy(strategy)
            self.signal_generators[key] = generator
        return generator

    def process_symbol(self, symbol: str, timeframe: str) -> None:
        """Process trading logic for a symbol."""
        try:
            if not self.session_manager.should_trade_symbol(symbol):
                return

            market_data_raw = self._get_market_data_sync(symbol, timeframe, bars=200)
            if not market_data_raw or len(market_data_raw) < MIN_BARS_WARMUP:
                # Not enough bars for reliable indicator values
                return
            
            latest_bar = market_data_raw[-1]
            closes = [bar['close'] for bar in market_data_raw]
            highs = [bar['high'] for bar in market_data_raw]
            lows = [bar['low'] for bar in market_data_raw]
            
            # Calculate comprehensive indicators
            indicators = self._calculate_indicators(closes, highs, lows)
            
            ohlcv = OHLCV(
                open=Decimal(str(latest_bar['open'])),
                high=Decimal(str(latest_bar['high'])),
                low=Decimal(str(latest_bar['low'])),
                close=Decimal(str(latest_bar['close'])),
                volume=Decimal(str(latest_bar['volume']))
            )
            
            market_data = MarketData(
                symbol=symbol,
                timestamp=latest_bar['timestamp'],
                ohlcv=ohlcv,
                indicators=indicators
            )
            
            # Generate signal with the strategy isolated to this instrument
            signal = self._get_signal_generator(symbol, timeframe).analyze_market_data(market_data)
            
            if signal:
                self.signal_count += 1
                
                # ===== ANALYSIS DISPLAY =====
                logger.info("=" * 70)
                logger.info(f"📊 SIGNAL ANALYSIS #{self.signal_count} - {symbol}")
                logger.info("=" * 70)
                logger.info(f"🎯 Direction:     {signal.direction.value}")
                logger.info(f"💪 Confidence:    {signal.confidence:.2%}")
                logger.info(f"⚡ Strength:      {signal.strength:.2f}")
                logger.info(f"📈 R:R Ratio:     {signal.metadata.get('risk_reward_ratio', 1.5):.1f}:1")
                logger.info("-" * 70)
                logger.info("📉 TECHNICAL INDICATORS:")
                
                # Display all indicators
                if 'rsi' in indicators:
                    rsi_val = indicators['rsi']
                    rsi_status = "Oversold" if rsi_val < 30 else "Overbought" if rsi_val > 70 else "Neutral"
                    logger.info(f"   RSI:           {rsi_val:.1f} ({rsi_status})")
                
                if 'macd' in indicators:
                    macd_val = indicators['macd']
                    macd_signal = "Bullish" if macd_val > 0 else "Bearish"
                    logger.info(f"   MACD:          {macd_val:.5f} ({macd_signal})")
                
                if 'adx' in indicators:
                    adx_val = indicators['adx']
                    trend_strength = "Strong" if adx_val > 25 else "Weak"
                    logger.info(f"   ADX:           {adx_val:.1f} ({trend_strength} trend)")
                
                if 'stoch_k' in indicators:
                    stoch_val = indicators['stoch_k']
                    stoch_status = "Oversold" if stoch_val < 20 else "Overbought" if stoch_val > 80 else "Neutral"
                    logger.info(f"   Stochastic:    {stoch_val:.1f} ({stoch_status})")
                
                if 'cci' in indicators:
                    cci_val = indicators['cci']
                    cci_status = "Oversold" if cci_val < -100 else "Overbought" if cci_val > 100 else "Neutral"
                    logger.info(f"   CCI:           {cci_val:.1f} ({cci_status})")
                
                if 'bb_width' in indicators:
                    logger.info(f"   BB Width:      {indicators['bb_width']:.5f}")
                
                if 'atr' in indicators:
                    logger.info(f"   ATR:           {indicators['atr']:.5f} (volatility)")
                
                logger.info("=" * 70)
                
                # Check position limits - allow multiple positions per symbol
                risk_params = self.session_manager.get_risk_parameters()
                max_positions = risk_params['max_positions']
                max_per_symbol = self.config.risk_management.max_positions_per_symbol
                
                if len(self.open_positions) >= max_positions:
                    logger.warning(f"❌ Max total positions reached ({max_positions})")
                    return
                
                # Count positions for this symbol
                symbol_position_count = sum(1 for key in self.open_positions.keys() if key.startswith(f"{symbol}_"))
                if symbol_position_count >= max_per_symbol:
                    logger.info(f"⚠️  Max positions for {symbol} reached ({symbol_position_count}/{max_per_symbol})")
                    return
                
                # Circuit breaker
                if self._consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
                    logger.error(
                        f"Circuit breaker: {self._consecutive_failures} consecutive failures. "
                        "Pausing order placement."
                    )
                    return

                # Calculate dynamic position size
                volume = self.calculate_position_size(symbol, signal)

                # Use ask/bid for SL/TP — not last bar close
                sym_info = mt5.symbol_info(symbol)
                if sym_info is None:
                    logger.error(f"Cannot get symbol info for {symbol}")
                    return

                stop_loss_pct     = signal.metadata.get('stop_loss', 0.0002)
                profit_target_pct = signal.metadata.get('profit_target', 0.0003)
                digits            = sym_info.digits

                if signal.direction == SignalDirection.BUY:
                    ref_price  = sym_info.ask
                    sl = round(ref_price * (1 - stop_loss_pct), digits)
                    tp = round(ref_price * (1 + profit_target_pct), digits)
                    order_type = "BUY"
                else:
                    ref_price  = sym_info.bid
                    sl = round(ref_price * (1 + stop_loss_pct), digits)
                    tp = round(ref_price * (1 - profit_target_pct), digits)
                    order_type = "SELL"
                
                # Risk validation before execution. Quantity is expressed in
                # units (lots x contract size) so risk math is instrument
                # independent; stop distance is the actual SL, not a notional
                # percentage.
                contract_size = _safe_float(
                    getattr(sym_info, 'trade_contract_size', 1.0), 1.0
                ) or 1.0
                risk_request = OrderRequest(
                    symbol=symbol,
                    side=OrderSide.BUY if order_type == "BUY" else OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=Decimal(str(volume)) * Decimal(str(contract_size)),
                    price=Decimal(str(ref_price)),
                    stop_loss=Decimal(str(sl)),
                    take_profit=Decimal(str(tp)),
                    time_in_force=TimeInForce.GTC,
                )
                validation = self.risk_manager.validate_trade(risk_request)
                if not validation.approved:
                    logger.warning(f"[RISK] Trade blocked for {symbol}: {validation.reason}")
                    return

                # Place order
                logger.info(f"[PLACING] {order_type} {symbol} {volume} lots | SL={sl:.{digits}f} TP={tp:.{digits}f}")

                order_result = self.mt_connector.place_order(
                    symbol=symbol,
                    order_type=order_type,
                    volume=volume,
                    sl=sl,
                    tp=tp,
                    comment="Enhanced_HFT"
                )

                if order_result:
                    self._consecutive_failures = 0  # reset circuit breaker
                    self.trade_count += 1

                    position_key = f"{symbol}_{int(datetime.now().timestamp())}"

                    if symbol not in self.position_counter:
                        self.position_counter[symbol] = 0
                    self.position_counter[symbol] += 1

                    logger.info(f"[OK] Trade #{self.trade_count} executed | ticket={order_result['order_id']} fill={order_result['price']:.{digits}f}")
                    logger.info("=" * 70)

                    self.open_positions[position_key] = {
                        'symbol': symbol,
                        'order_id': order_result['order_id'],
                        'direction': signal.direction,
                        'volume': volume,
                        'entry_price': order_result['price'],
                        'sl': sl,
                        'tp': tp,
                        'timestamp': datetime.now(),
                        'confidence': signal.confidence
                    }
                else:
                    self._consecutive_failures += 1
                    logger.error(f"[FAIL] Order failed for {symbol} (failure #{self._consecutive_failures})")
                    logger.info("=" * 70)
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}", exc_info=True)
    
    def _calculate_indicators(self, closes: list, highs: list, lows: list) -> Dict[str, float]:
        """Calculate comprehensive technical indicators using shared module."""
        if len(closes) < 50:
            return {}
        
        try:
            # Moving Averages
            sma_20 = float(np.mean(closes[-20:]))
            sma_50 = float(np.mean(closes[-50:]))
            ema_12 = calculate_ema(closes, 12)
            ema_26 = calculate_ema(closes, 26)
            
            # MACD (true signal EMA — Bug 4 fixed via shared module)
            macd_line, macd_signal_line, macd_histogram = calculate_macd(closes)
            
            # RSI
            rsi = calculate_rsi(closes)
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(closes)
            bb_width = (bb_upper - bb_lower) / bb_middle if bb_middle > 0 else 0
            
            # Stochastic Oscillator
            stoch_k, stoch_d = calculate_stochastic(closes, highs, lows)
            
            # ADX (Wilder-smoothed — Bug 3 fixed via shared module)
            adx = calculate_adx(closes, highs, lows)
            
            # ATR
            atr = calculate_atr(closes, highs, lows)
            
            # CCI
            cci = calculate_cci(closes, highs, lows)
            
            return {
                'sma_20': sma_20,
                'sma_50': sma_50,
                'ema_12': ema_12,
                'ema_26': ema_26,
                'macd': macd_line,
                'macd_signal': macd_signal_line,
                'macd_histogram': macd_histogram,
                'rsi': rsi,
                'bb_upper': bb_upper,
                'bb_middle': bb_middle,
                'bb_lower': bb_lower,
                'bb_width': bb_width,
                'stoch_k': stoch_k,
                'stoch_d': stoch_d,
                'adx': adx,
                'atr': atr,
                'cci': cci
            }
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return {}
    
    def monitor_positions(self) -> None:
        """Monitor and update open positions."""
        try:
            positions = self.mt_connector.get_positions()
            
            # Get current open order IDs from MT5
            current_order_ids = set()
            if positions:
                for pos in positions:
                    current_order_ids.add(pos.get('ticket', pos.get('order_id')))
            
            # Check for closed positions
            closed_position_keys = []
            for pos_key, pos_info in self.open_positions.items():
                if pos_info['order_id'] not in current_order_ids:
                    closed_position_keys.append(pos_key)
            
            # Process closed positions
            for pos_key in closed_position_keys:
                pos_info = self.open_positions[pos_key]
                symbol = pos_info['symbol']
                
                logger.info(f"📍 Position closed: {symbol} (ID: {pos_key})")
                
                # Update counter
                if symbol in self.position_counter:
                    self.position_counter[symbol] = max(0, self.position_counter[symbol] - 1)
                
                # Track win/loss from the broker's realized PnL for this
                # position and feed it to the performance monitor.
                order_id = pos_info['order_id']
                pnl = self.mt_connector.get_realized_pnl(order_id)

                if pnl is None:
                    logger.warning(
                        f"No realized P&L available for {symbol} ticket={order_id}; "
                        "excluding it from performance stats"
                    )
                else:
                    pnl = float(pnl)
                    if pnl > 0:
                        self.win_count += 1
                        logger.info(f"   ✅ WIN (P&L: {pnl:.2f})")
                    elif pnl < 0:
                        self.loss_count += 1
                        logger.info(f"   ❌ LOSS (P&L: {pnl:.2f})")
                    else:
                        logger.info("   ➖ BREAKEVEN (P&L: 0.00)")

                    direction = pos_info.get('direction')
                    side = (
                        OrderSide.BUY
                        if str(getattr(direction, 'value', direction)).upper() == 'BUY'
                        else OrderSide.SELL
                    )
                    self.performance_monitor.record_closed_trade(
                        symbol=symbol,
                        side=side,
                        quantity=pos_info.get('volume', 0),
                        entry_price=pos_info.get('entry_price'),
                        gross_pnl=Decimal(str(pnl)),
                        order_id=order_id,
                        trade_id=pos_key,
                    )
                
                del self.open_positions[pos_key]
            
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
    
    def log_status(self) -> None:
        """Log current bot status."""
        try:
            account_info = self._get_account_info_sync()
            session_config = self.session_manager.get_session_config()
            
            if account_info:
                win_rate = (self.win_count / max(self.win_count + self.loss_count, 1)) * 100
                
                # Count positions per symbol
                symbol_counts = {}
                for pos_key, pos_info in self.open_positions.items():
                    symbol = pos_info['symbol']
                    symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
                
                logger.info("=" * 70)
                logger.info("📊 ENHANCED BOT STATUS")
                logger.info("-" * 70)
                logger.info(f"Session:          {session_config.name if session_config else 'All Sessions'}")
                logger.info(f"Balance:          ${account_info['balance']:.2f} USD")
                logger.info(f"Equity:           ${account_info['equity']:.2f}")
                logger.info(f"Profit/Loss:      ${account_info['equity'] - account_info['balance']:.2f}")
                logger.info(f"Open Positions:   {len(self.open_positions)}")
                
                if symbol_counts:
                    logger.info(f"Positions by Symbol:")
                    for symbol, count in symbol_counts.items():
                        logger.info(f"   {symbol}: {count}")
                
                logger.info(f"Signals Generated: {self.signal_count}")
                logger.info(f"Trades Placed:    {self.trade_count}")
                logger.info(f"Win Rate:         {win_rate:.1f}% ({self.win_count}W / {self.loss_count}L)")

                perf = self.performance_monitor.get_real_time_metrics()
                if perf.get('total_trades'):
                    logger.info(
                        f"Realized P&L:     ${perf['total_pnl']:.2f} "
                        f"(profit factor {perf['profit_factor']:.2f})"
                    )
                logger.info("=" * 70)
        except Exception as e:
            logger.error(f"Error logging status: {e}")
    
    def start(self) -> None:
        """Start the enhanced trading bot."""
        try:
            logger.info("=" * 60)
            logger.info("ENHANCED HFT TRADING BOT")
            logger.info("=" * 60)

            # Connect to MetaTrader
            if not self.mt_connector.connect():
                logger.error("Failed to connect to MetaTrader")
                return

            logger.info("[OK] Connected to MetaTrader 5")

            account_info = self._get_account_info_sync()
            if account_info:
                logger.info(f"Account: {account_info['login']}")
                logger.info(f"Balance: {account_info['balance']} USD")

            # Baseline daily risk tracking on live equity now that we are
            # connected (the constructor runs before connect()).
            self.risk_manager.reset_daily_baseline()

            # Sync any existing open positions before starting the loop
            self._sync_positions_from_broker()

            logger.info("=" * 60)
            logger.info("[START] Enhanced Bot Started — Press Ctrl+C to stop")
            logger.info("=" * 60)

            self.running = True
            last_status_time = datetime.now()

            while self.running:
                # Connection health check
                if not self._is_connected():
                    logger.warning("MT5 connection lost")
                    if not self._reconnect():
                        break

                try:
                    self.session_manager.update_session()

                    # Enforce stops and portfolio-level risk limits before
                    # looking for new entries.
                    self.risk_manager.monitor_positions()
                    if self.risk_manager.emergency_stop_active:
                        logger.critical(
                            "Emergency stop active — halting the trading loop and "
                            "closing positions"
                        )
                        self.running = False
                        break

                    for symbol in self.config.trading.symbols:
                        for timeframe in self.config.trading.timeframes:
                            if not self.running:
                                break
                            self.process_symbol(symbol, timeframe)

                    self.monitor_positions()

                    if (datetime.now() - last_status_time).total_seconds() >= 60:
                        self.log_status()
                        last_status_time = datetime.now()

                    time.sleep(3)

                except KeyboardInterrupt:
                    logger.info("\n[WARNING] Keyboard interrupt received")
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}", exc_info=True)
                    time.sleep(5)

        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            self.stop()

    def _is_connected(self) -> bool:
        """Quick connection health check."""
        try:
            return self._get_account_info_sync() is not None
        except Exception:
            return False

    def _reconnect(self) -> bool:
        """Attempt to reconnect to MT5 with backoff."""
        for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
            logger.warning(f"Reconnect attempt {attempt}/{MAX_RECONNECT_ATTEMPTS}...")
            self.mt_connector.disconnect()
            time.sleep(RECONNECT_DELAY)
            if self.mt_connector.connect():
                logger.info("[OK] Reconnected to MT5")
                self._sync_positions_from_broker()
                return True
        logger.error("All reconnect attempts failed — stopping bot")
        return False
    
    def stop(self) -> None:
        """Stop the trading bot — close all open positions first."""
        logger.info("=" * 60)
        logger.info("Stopping Enhanced Bot — closing all positions...")
        logger.info("=" * 60)
        self.running = False

        self._close_all_positions()
        self.log_status()
        self.mt_connector.disconnect()
        logger.info("[OK] Bot stopped")

    def _close_all_positions(self) -> None:
        """Close every open position via MT5."""
        try:
            mt_positions = self.mt_connector.get_positions()
            if not mt_positions:
                logger.info("No open positions to close")
                return

            closed = 0
            for pos in mt_positions:
                ticket = pos['ticket']
                if self.mt_connector.close_position(ticket):
                    closed += 1
                    logger.info(f"[CLOSED] ticket={ticket} {pos['symbol']}")
                else:
                    logger.error(f"[FAIL] Could not close ticket={ticket}")

            self.open_positions.clear()
            self.position_counter.clear()
            logger.info(f"Closed {closed}/{len(mt_positions)} positions")
        except Exception as e:
            logger.error(f"Error in _close_all_positions: {e}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"\n[WARNING] Received signal {signum}")
        self.stop()
        sys.exit(0)

def main():
    """Main entry point."""
    import sys
    
    auto_mode = '--auto' in sys.argv or '-y' in sys.argv
    
    if not auto_mode:
        print("\n")
        print("╔" + "=" * 58 + "╗")
        print("║" + " " * 12 + "ENHANCED HFT TRADING BOT" + " " * 22 + "║")
        print("╚" + "=" * 58 + "╝")
        print()
        print("Enhanced Features:")
        print("  [OK] Multi-layer signal analysis (5 indicators)")
        print("  [OK] Dynamic position sizing based on confidence")
        print("  [OK] Adaptive risk management")
        print("  [OK] Support/Resistance detection")
        print("  [OK] Better win rate and accuracy")
        print()
        
        response = input("Start enhanced bot? (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y']:
            print("\n[CANCELLED] Bot start cancelled")
            return
    
    print("\n[START] Starting enhanced bot...\n")
    
    bot = EnhancedBot()
    bot.start()

if __name__ == "__main__":
    main()
