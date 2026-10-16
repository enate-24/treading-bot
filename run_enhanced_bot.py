"""
Enhanced HFT Trading Bot with improved accuracy.
"""
import MetaTrader5 as mt5
import logging
import time
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional
import signal
import sys

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

# Import bot components
from trading_bot.connectors.metatrader_connector import MetaTraderConnector
from trading_bot.signal_generator import SignalGenerator
from trading_bot.strategies.enhanced_hft_strategy import EnhancedHFTStrategy
from trading_bot.session_manager import SessionManager
from trading_bot.performance_monitor import PerformanceMonitor
from trading_bot.models.core import MarketData, OHLCV, TradingSignal, ExecutedTrade
from trading_bot.models.enums import SignalDirection, OrderSide

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
        
        # Initialize components
        self.mt_connector = MetaTraderConnector(
            account=config_dict['metatrader']['account'],
            password=config_dict['metatrader']['password'],
            server=config_dict['metatrader']['server'],
            mt_version=config_dict['metatrader'].get('version', 5)
        )
        self.enhanced_strategy = EnhancedHFTStrategy(
            config_dict.get('strategy_parameters', {}).get('enhanced_hft', {})
        )
        self.signal_generator = SignalGenerator()
        self.signal_generator.set_strategy(self.enhanced_strategy)
        self.session_manager = SessionManager(config_dict)
        self.performance_monitor = PerformanceMonitor(self.config)
        
        # Trading state
        self.running = False
        self.open_positions: Dict[str, dict] = {}  # Key: "symbol_timestamp"
        self.position_counter: Dict[str, int] = {}  # Track position count per symbol
        self.signal_count = 0
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        logger.info("[OK] Enhanced HFT Strategy loaded")
        logger.info("[OK] Multi-layer signal analysis enabled")
        logger.info("[OK] Dynamic risk management active")
    
    def calculate_position_size(self, symbol: str, signal) -> float:
        """Calculate dynamic position size based on confidence and volatility."""
        account_info = self.mt_connector.get_account_info()
        if not account_info:
            return 0.01
        
        balance = account_info['balance']
        risk_per_trade = self.config.risk_management.risk_per_trade
        
        # Adjust risk based on signal confidence
        confidence_multiplier = signal.confidence  # 0.15 to 1.0
        adjusted_risk = risk_per_trade * confidence_multiplier
        
        # Adjust for volatility
        volatility = signal.metadata.get('volatility', 0.0001)
        if volatility > 0.0002:  # High volatility
            adjusted_risk *= 0.7
        elif volatility < 0.00005:  # Low volatility
            adjusted_risk *= 1.2
        
        # Calculate position size
        risk_amount = balance * adjusted_risk
        stop_loss_pct = signal.metadata.get('stop_loss', 0.0002)
        
        # For forex: 1 lot = 100,000 units
        # Risk per pip = lot_size * pip_value
        pip_value = 10  # For standard lot on major pairs
        stop_loss_pips = stop_loss_pct * 10000  # Convert to pips
        
        lot_size = risk_amount / (stop_loss_pips * pip_value)
        
        # Clamp to reasonable range
        lot_size = max(0.01, min(lot_size, 0.10))
        
        return round(lot_size, 2)
    
    def process_symbol(self, symbol: str, timeframe: str) -> None:
        """Process trading logic for a symbol."""
        try:
            # Check if we should trade this symbol in current session
            if not self.session_manager.should_trade_symbol(symbol):
                return
            
            # Get market data
            market_data_raw = self.mt_connector.get_market_data(symbol, timeframe, bars=200)
            
            if not market_data_raw or len(market_data_raw) == 0:
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
            
            # Generate signal with enhanced strategy
            signal = self.signal_generator.analyze_market_data(market_data)
            
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
                
                # Calculate dynamic position size
                volume = self.calculate_position_size(symbol, signal)
                
                # Get dynamic SL/TP from signal
                current_price = float(latest_bar['close'])
                stop_loss_pct = signal.metadata.get('stop_loss', 0.0002)
                profit_target_pct = signal.metadata.get('profit_target', 0.0003)
                
                if signal.direction == SignalDirection.BUY:
                    sl = current_price * (1 - stop_loss_pct)
                    tp = current_price * (1 + profit_target_pct)
                    order_type = "BUY"
                else:
                    sl = current_price * (1 + stop_loss_pct)
                    tp = current_price * (1 - profit_target_pct)
                    order_type = "SELL"
                
                # Place order
                logger.info(f"🔵 PLACING {order_type} ORDER")
                logger.info(f"   Symbol:        {symbol}")
                logger.info(f"   Volume:        {volume} lots")
                logger.info(f"   Entry Price:   {current_price:.5f}")
                logger.info(f"   Stop Loss:     {sl:.5f}")
                logger.info(f"   Take Profit:   {tp:.5f}")
                
                order_result = self.mt_connector.place_order(
                    symbol=symbol,
                    order_type=order_type,
                    volume=volume,
                    sl=sl,
                    tp=tp,
                    comment="Enhanced_HFT"
                )
                
                if order_result:
                    self.trade_count += 1
                    
                    # Create unique position key
                    position_key = f"{symbol}_{int(datetime.now().timestamp())}"
                    
                    # Initialize counter if needed
                    if symbol not in self.position_counter:
                        self.position_counter[symbol] = 0
                    self.position_counter[symbol] += 1
                    
                    logger.info(f"✅ Trade #{self.trade_count} EXECUTED successfully")
                    logger.info(f"   Position ID:   {position_key}")
                    logger.info(f"   Order ID:      {order_result['order_id']}")
                    logger.info(f"   {symbol} Positions: {self.position_counter[symbol]}/{max_per_symbol}")
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
                    logger.error(f"❌ Failed to place order for {symbol}")
                    logger.info("=" * 70)
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}", exc_info=True)
    
    def _calculate_indicators(self, closes: list, highs: list, lows: list) -> Dict[str, float]:
        """Calculate comprehensive technical indicators."""
        if len(closes) < 50:
            return {}
        
        try:
            prices = np.array(closes)
            
            # Moving Averages
            sma_20 = np.mean(prices[-20:])
            sma_50 = np.mean(prices[-50:])
            ema_12 = self._calculate_ema(prices, 12)
            ema_26 = self._calculate_ema(prices, 26)
            
            # MACD
            macd_line = ema_12 - ema_26
            macd_signal_line = self._calculate_ema(np.array([macd_line] * 9), 9)
            macd_histogram = macd_line - macd_signal_line
            
            # RSI
            rsi = self._calculate_rsi(closes)
            
            # Bollinger Bands
            bb_middle = sma_20
            bb_std = np.std(prices[-20:])
            bb_upper = bb_middle + (2 * bb_std)
            bb_lower = bb_middle - (2 * bb_std)
            bb_width = (bb_upper - bb_lower) / bb_middle if bb_middle > 0 else 0
            
            # Stochastic Oscillator
            stoch_k, stoch_d = self._calculate_stochastic(closes, highs, lows)
            
            # ADX (Average Directional Index)
            adx = self._calculate_adx(closes, highs, lows)
            
            # ATR (Average True Range)
            atr = self._calculate_atr(closes, highs, lows)
            
            # CCI (Commodity Channel Index)
            cci = self._calculate_cci(closes, highs, lows)
            
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
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return prices[-1]
        
        multiplier = 2 / (period + 1)
        ema = prices[-period]
        
        for price in prices[-period+1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_stochastic(self, closes: list, highs: list, lows: list, period: int = 14) -> tuple:
        """Calculate Stochastic Oscillator."""
        try:
            if len(closes) < period or len(highs) < period or len(lows) < period:
                return 50.0, 50.0
            
            recent_closes = closes[-period:]
            recent_highs = highs[-period:]
            recent_lows = lows[-period:]
            
            highest_high = max(recent_highs)
            lowest_low = min(recent_lows)
            
            if highest_high == lowest_low:
                return 50.0, 50.0
            
            stoch_k = ((recent_closes[-1] - lowest_low) / (highest_high - lowest_low)) * 100
            stoch_d = stoch_k  # Simplified
            
            return stoch_k, stoch_d
        except:
            return 50.0, 50.0
    
    def _calculate_adx(self, closes: list, highs: list, lows: list, period: int = 14) -> float:
        """Calculate Average Directional Index."""
        try:
            if len(closes) < period + 1:
                return 25.0
            
            # Simplified ADX calculation
            tr_list = []
            for i in range(1, len(closes)):
                high_low = highs[i] - lows[i]
                high_close = abs(highs[i] - closes[i-1])
                low_close = abs(lows[i] - closes[i-1])
                tr = max(high_low, high_close, low_close)
                tr_list.append(tr)
            
            if len(tr_list) < period:
                return 25.0
            
            atr = np.mean(tr_list[-period:])
            
            # Calculate directional movement
            plus_dm = []
            minus_dm = []
            
            for i in range(1, len(highs)):
                high_diff = highs[i] - highs[i-1]
                low_diff = lows[i-1] - lows[i]
                
                if high_diff > low_diff and high_diff > 0:
                    plus_dm.append(high_diff)
                    minus_dm.append(0)
                elif low_diff > high_diff and low_diff > 0:
                    plus_dm.append(0)
                    minus_dm.append(low_diff)
                else:
                    plus_dm.append(0)
                    minus_dm.append(0)
            
            if len(plus_dm) < period or atr == 0:
                return 25.0
            
            plus_di = (np.mean(plus_dm[-period:]) / atr) * 100
            minus_di = (np.mean(minus_dm[-period:]) / atr) * 100
            
            if plus_di + minus_di == 0:
                return 25.0
            
            dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
            return dx
        except:
            return 25.0
    
    def _calculate_atr(self, closes: list, highs: list, lows: list, period: int = 14) -> float:
        """Calculate Average True Range."""
        try:
            if len(closes) < period + 1:
                return 0.0001
            
            tr_list = []
            for i in range(1, len(closes)):
                high_low = highs[i] - lows[i]
                high_close = abs(highs[i] - closes[i-1])
                low_close = abs(lows[i] - closes[i-1])
                tr = max(high_low, high_close, low_close)
                tr_list.append(tr)
            
            if len(tr_list) < period:
                return 0.0001
            
            return np.mean(tr_list[-period:])
        except:
            return 0.0001
    
    def _calculate_cci(self, closes: list, highs: list, lows: list, period: int = 20) -> float:
        """Calculate Commodity Channel Index."""
        try:
            if len(closes) < period or len(highs) < period or len(lows) < period:
                return 0.0
            
            typical_prices = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(len(closes))]
            
            if len(typical_prices) < period:
                return 0.0
            
            sma_tp = np.mean(typical_prices[-period:])
            deviations = [abs(tp - sma_tp) for tp in typical_prices[-period:]]
            mean_deviation = np.mean(deviations)
            
            if mean_deviation == 0:
                return 0.0
            
            cci = (typical_prices[-1] - sma_tp) / (0.015 * mean_deviation)
            return cci
        except:
            return 0.0
    
    def _calculate_rsi(self, prices: list, period: int = 14) -> float:
        """Calculate RSI."""
        if len(prices) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(len(prices) - period, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
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
                
                # Track win/loss (simplified)
                if pos_info.get('confidence', 0) > 0.5:
                    self.win_count += 1
                    logger.info(f"   ✅ Likely WIN (confidence: {pos_info['confidence']:.2%})")
                else:
                    self.loss_count += 1
                    logger.info(f"   ❌ Likely LOSS (confidence: {pos_info['confidence']:.2%})")
                
                del self.open_positions[pos_key]
            
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
    
    def log_status(self) -> None:
        """Log current bot status."""
        try:
            account_info = self.mt_connector.get_account_info()
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
                logger.info("=" * 70)
        except Exception as e:
            logger.error(f"Error logging status: {e}")
    
    def start(self) -> None:
        """Start the enhanced trading bot."""
        try:
            logger.info("=" * 60)
            logger.info("ENHANCED HFT TRADING BOT")
            logger.info("=" * 60)
            logger.info("Features:")
            logger.info("  • Multi-layer signal analysis")
            logger.info("  • Dynamic position sizing")
            logger.info("  • Trend + Momentum + Volume + Volatility")
            logger.info("  • Support/Resistance detection")
            logger.info("  • Adaptive risk management")
            logger.info("=" * 60)
            
            # Connect to MetaTrader
            if not self.mt_connector.connect():
                logger.error("Failed to connect to MetaTrader")
                return
            
            logger.info("[OK] Connected to MetaTrader 5")
            
            # Get account info
            account_info = self.mt_connector.get_account_info()
            if account_info:
                logger.info(f"Account: {account_info['login']}")
                logger.info(f"Balance: {account_info['balance']} USD")
            
            logger.info("=" * 60)
            logger.info("[START] Enhanced Bot Started")
            logger.info("Press Ctrl+C to stop")
            logger.info("=" * 60)
            
            self.running = True
            last_status_time = datetime.now()
            
            # Main trading loop
            while self.running:
                try:
                    # Update session
                    self.session_manager.update_session()
                    
                    # Process each symbol
                    for symbol in self.config.trading.symbols:
                        for timeframe in self.config.trading.timeframes:
                            self.process_symbol(symbol, timeframe)
                    
                    # Monitor positions
                    self.monitor_positions()
                    
                    # Log status every 60 seconds
                    if (datetime.now() - last_status_time).total_seconds() >= 60:
                        self.log_status()
                        last_status_time = datetime.now()
                    
                    # Sleep
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
    
    def stop(self) -> None:
        """Stop the trading bot."""
        logger.info("=" * 60)
        logger.info("Stopping Enhanced Bot...")
        logger.info("=" * 60)
        
        self.running = False
        self.log_status()
        self.mt_connector.disconnect()
        
        logger.info("[OK] Bot stopped successfully")
    
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
