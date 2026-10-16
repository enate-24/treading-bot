"""Automated trading bot for MetaTrader 4/5 platforms."""

import logging
import time
import signal
import sys
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any

from trading_bot.connectors import MetaTraderConnector
from trading_bot.signal_generator import SignalGenerator
from trading_bot.strategies.swing_trading_strategy import SwingTradingStrategy
from trading_bot.strategies.scalping_strategy import ScalpingStrategy
from trading_bot.strategies.hft_strategy import HFTStrategy
from trading_bot.performance_monitor import PerformanceMonitor
from trading_bot.models import (
    MarketData, OHLCV, TradingSignal, SignalDirection,
    ExecutedTrade, OrderSide
)
import json


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('metatrader_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Fix Windows console encoding for Unicode characters
import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

logger = logging.getLogger(__name__)


class MetaTraderBot:
    """Fully automated trading bot for MetaTrader platforms."""
    
    def __init__(self, config_path: str = "config/metatrader_config.json"):
        """Initialize MetaTrader trading bot.
        
        Args:
            config_path: Path to MetaTrader configuration file
        """
        self.running = False
        self.config_path = config_path
        
        logger.info("=" * 60)
        logger.info("Initializing MetaTrader Trading Bot")
        logger.info("=" * 60)
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        logger.info(f"✓ Configuration loaded from {config_path}")
        
        # Initialize MetaTrader connector
        mt_config = self.config['metatrader']
        self.mt_connector = MetaTraderConnector(
            account=mt_config['account'],
            password=mt_config['password'],
            server=mt_config['server'],
            mt_version=mt_config.get('version', 5)
        )
        
        if not self.mt_connector.connect():
            raise ConnectionError("Failed to connect to MetaTrader terminal")
        
        logger.info("✓ Connected to MetaTrader")
        
        # Log account info
        account_info = self.mt_connector.get_account_info()
        if account_info:
            logger.info(f"  Account: {account_info['login']}")
            logger.info(f"  Balance: {account_info['balance']} {account_info['currency']}")
            logger.info(f"  Leverage: 1:{account_info['leverage']}")
        
        # Initialize signal generator with strategy
        self.signal_generator = SignalGenerator()
        self.strategy_name = self.config['trading'].get('strategy', 'swing_trading')
        
        if self.strategy_name == 'hft':
            hft_params = self.config['trading'].get('hft_parameters', {})
            strategy = HFTStrategy(parameters=hft_params)
            logger.info("✓ Using High-Frequency Trading (HFT) Strategy")
        elif self.strategy_name == 'scalping':
            strategy = ScalpingStrategy()
            logger.info("✓ Using Scalping Strategy")
        else:
            strategy = SwingTradingStrategy()
            logger.info("✓ Using Swing Trading Strategy")
        
        self.signal_generator.set_strategy(strategy)
        
        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor(risk_free_rate=0.02)
        logger.info("✓ Performance Monitor initialized")
        
        # Trading parameters
        self.symbols = self.config['trading'].get('symbols', ['EURUSD'])
        self.timeframes = self.config['trading'].get('timeframes', ['H1'])
        self.risk_per_trade = self.config['trading'].get('risk_per_trade', 0.01)
        self.max_positions = self.config['trading'].get('max_positions', 3)
        
        # Track open positions
        self.open_positions: Dict[str, Any] = {}
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        logger.info(f"✓ Monitoring {len(self.symbols)} symbol(s): {', '.join(self.symbols)}")
        logger.info("=" * 60)
        logger.info("MetaTrader Bot Initialization Complete")
        logger.info("=" * 60)
    
    def calculate_position_size(self, symbol: str, signal: TradingSignal) -> float:
        """Calculate position size based on risk parameters.
        
        Args:
            symbol: Trading symbol
            signal: Trading signal
            
        Returns:
            Position size in lots
        """
        try:
            account_info = self.mt_connector.get_account_info()
            if not account_info:
                return 0.01  # Minimum lot size
            
            balance = account_info['balance']
            risk_amount = balance * self.risk_per_trade
            
            # Get symbol info for contract size
            symbol_info = self.mt_connector.get_symbol_info(symbol)
            if not symbol_info:
                return 0.01
            
            # Calculate stop loss distance from metadata
            stop_loss_pct = signal.metadata.get('stop_loss', 0.015)
            current_price = symbol_info['bid']
            stop_distance = current_price * stop_loss_pct
            
            # Calculate position size
            # Risk Amount = Position Size * Stop Distance * Contract Size
            contract_size = symbol_info['trade_contract_size']
            position_size = risk_amount / (stop_distance * contract_size)
            
            # Round to volume step
            volume_step = symbol_info['volume_step']
            position_size = round(position_size / volume_step) * volume_step
            
            # Ensure within min/max limits
            position_size = max(symbol_info['volume_min'], position_size)
            position_size = min(symbol_info['volume_max'], position_size)
            
            # Adjust by signal strength and confidence
            position_size *= (signal.strength * signal.confidence)
            
            return round(position_size, 2)
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.01  # Return minimum lot size on error
    
    def process_symbol(self, symbol: str, timeframe: str) -> None:
        """Process trading logic for a symbol.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe to analyze
        """
        try:
            # Get market data
            market_data_raw = self.mt_connector.get_market_data(symbol, timeframe, bars=100)
            
            if not market_data_raw or len(market_data_raw) == 0:
                return
            
            # Convert to MarketData object
            latest_bar = market_data_raw[-1]
            
            # Calculate simple indicators (RSI, SMA)
            closes = [bar['close'] for bar in market_data_raw]
            indicators = self._calculate_indicators(closes)
            
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
            
            # Generate signal
            signal = self.signal_generator.analyze_market_data(market_data)
            
            if signal:
                logger.info(f"📊 Signal: {signal.direction.value} {symbol}")
                logger.info(f"   Strength: {signal.strength:.2f}, Confidence: {signal.confidence:.2f}")
                
                # Check if we can open new position
                if len(self.open_positions) >= self.max_positions:
                    logger.warning(f"⚠️  Max positions reached ({self.max_positions})")
                    return
                
                # Check if already have position in this symbol
                if symbol in self.open_positions:
                    logger.info(f"ℹ️  Already have position in {symbol}")
                    return
                
                # Calculate position size
                volume = self.calculate_position_size(symbol, signal)
                
                # Calculate stop loss and take profit
                current_price = float(latest_bar['close'])
                stop_loss_pct = signal.metadata.get('stop_loss', 0.015)
                profit_target_pct = signal.metadata.get('profit_target', 0.03)
                
                if signal.direction == SignalDirection.BUY:
                    sl = current_price * (1 - stop_loss_pct)
                    tp = current_price * (1 + profit_target_pct)
                    order_type = "BUY"
                else:
                    sl = current_price * (1 + stop_loss_pct)
                    tp = current_price * (1 - profit_target_pct)
                    order_type = "SELL"
                
                # Place order
                logger.info(f"🎯 Placing {order_type} order: {volume} lots {symbol}")
                logger.info(f"   SL: {sl:.5f}, TP: {tp:.5f}")
                
                order_result = self.mt_connector.place_order(
                    symbol=symbol,
                    order_type=order_type,
                    volume=volume,
                    sl=sl,
                    tp=tp,
                    comment=f"{signal.strategy}"
                )
                
                if order_result:
                    logger.info(f"✅ Order placed successfully: {order_result['order_id']}")
                    
                    # Track position
                    self.open_positions[symbol] = {
                        'order_id': order_result['order_id'],
                        'direction': signal.direction,
                        'volume': volume,
                        'entry_price': order_result['price'],
                        'sl': sl,
                        'tp': tp,
                        'timestamp': datetime.now()
                    }
                    
                    # Record trade for performance tracking
                    trade = ExecutedTrade(
                        trade_id=str(order_result['order_id']),
                        symbol=symbol,
                        side=OrderSide.BUY if signal.direction == SignalDirection.BUY else OrderSide.SELL,
                        quantity=Decimal(str(volume)),
                        price=Decimal(str(order_result['price'])),
                        fee=Decimal('0'),
                        timestamp=datetime.now(),
                        order_id=str(order_result['order_id'])
                    )
                    self.performance_monitor.update_trade_metrics(trade)
                    
                else:
                    logger.error(f"❌ Failed to place order for {symbol}")
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}", exc_info=True)
    
    def _calculate_indicators(self, closes: list) -> Dict[str, float]:
        """Calculate technical indicators.
        
        Args:
            closes: List of closing prices
            
        Returns:
            Dictionary of indicator values
        """
        indicators = {}
        
        try:
            # RSI
            if len(closes) >= 14:
                indicators['RSI'] = self._calculate_rsi(closes, 14)
            
            # SMA 20
            if len(closes) >= 20:
                indicators['SMA_20'] = sum(closes[-20:]) / 20
            
            # SMA 50
            if len(closes) >= 50:
                indicators['SMA_50'] = sum(closes[-50:]) / 50
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
        
        return indicators
    
    def _calculate_rsi(self, prices: list, period: int = 14) -> float:
        """Calculate RSI indicator.
        
        Args:
            prices: List of prices
            period: RSI period
            
        Returns:
            RSI value
        """
        if len(prices) < period + 1:
            return 50.0
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [max(d, 0) for d in deltas]
        losses = [max(-d, 0) for d in deltas]
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def monitor_positions(self) -> None:
        """Monitor and update open positions."""
        try:
            # Get current positions from MT
            mt_positions = self.mt_connector.get_positions()
            
            # Update our tracking
            current_symbols = {pos['symbol'] for pos in mt_positions}
            
            # Remove closed positions from tracking
            closed_symbols = set(self.open_positions.keys()) - current_symbols
            for symbol in closed_symbols:
                logger.info(f"📍 Position closed: {symbol}")
                del self.open_positions[symbol]
            
            # Log position status
            if mt_positions:
                total_profit = sum(pos['profit'] for pos in mt_positions)
                logger.info(f"💼 Open Positions: {len(mt_positions)}, Total P&L: {total_profit:.2f}")
            
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
    
    def log_status(self) -> None:
        """Log current bot status."""
        try:
            account_info = self.mt_connector.get_account_info()
            if not account_info:
                return
            
            perf_metrics = self.performance_monitor.get_real_time_metrics()
            
            logger.info("=" * 60)
            logger.info("BOT STATUS")
            logger.info("-" * 60)
            logger.info(f"Balance:          {account_info['balance']:.2f} {account_info['currency']}")
            logger.info(f"Equity:           {account_info['equity']:.2f}")
            logger.info(f"Free Margin:      {account_info['free_margin']:.2f}")
            logger.info(f"Open Positions:   {len(self.open_positions)}")
            
            if perf_metrics.get('total_trades', 0) > 0:
                logger.info(f"Total Trades:     {perf_metrics['total_trades']}")
                logger.info(f"Win Rate:         {perf_metrics['win_rate']:.2%}")
                logger.info(f"Total P&L:        {perf_metrics['total_pnl']:.2f}")
            
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error logging status: {e}")
    
    def start(self) -> None:
        """Start the trading bot."""
        self.running = True
        
        logger.info("🚀 MetaTrader Bot Started")
        logger.info("Press Ctrl+C to stop")
        logger.info("")
        
        update_counter = 0
        
        try:
            while self.running:
                # Process each symbol
                for symbol in self.symbols:
                    for timeframe in self.timeframes:
                        self.process_symbol(symbol, timeframe)
                
                # Monitor positions
                self.monitor_positions()
                
                # Log status every 10 iterations
                update_counter += 1
                if update_counter % 10 == 0:
                    self.log_status()
                
                # Sleep between iterations (adjust based on strategy)
                if self.strategy_name == 'hft':
                    time.sleep(5)   # Check every 5 seconds for HFT
                else:
                    time.sleep(60)  # Check every minute for other strategies
                
        except KeyboardInterrupt:
            logger.info("\n⏸️  Keyboard interrupt received")
            self.stop()
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}", exc_info=True)
            self.stop()
    
    def stop(self) -> None:
        """Stop the bot gracefully."""
        logger.info("=" * 60)
        logger.info("Stopping MetaTrader Bot...")
        logger.info("=" * 60)
        
        self.running = False
        
        # Generate final report
        report = self.performance_monitor.generate_performance_report('all')
        logger.info("FINAL PERFORMANCE REPORT")
        logger.info("-" * 60)
        logger.info(f"Total Trades:     {report.total_trades}")
        logger.info(f"Win Rate:         {report.win_rate:.2%}")
        logger.info(f"Total P&L:        {report.total_pnl:.2f}")
        logger.info(f"Sharpe Ratio:     {report.sharpe_ratio:.2f}")
        logger.info(f"Max Drawdown:     {report.max_drawdown:.2%}")
        logger.info("=" * 60)
        
        # Disconnect from MetaTrader
        self.mt_connector.disconnect()
        logger.info("✓ Disconnected from MetaTrader")
        
        logger.info("MetaTrader Bot Stopped")
        logger.info("=" * 60)
    
    def signal_handler(self, signum, frame):
        """Handle system signals."""
        logger.info(f"\n⚠️  Received signal {signum}")
        self.stop()
        sys.exit(0)


def main():
    """Main entry point."""
    import sys
    
    # Check for --auto flag to skip prompts
    auto_mode = '--auto' in sys.argv or '-y' in sys.argv
    
    if not auto_mode:
        print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║        METATRADER AUTOMATED TRADING BOT                  ║
    ║                                                          ║
    ║  ⚠️  WARNING: This bot trades with REAL MONEY           ║
    ║                                                          ║
    ║  Requirements:                                           ║
    ║  • MetaTrader 5 terminal must be running                 ║
    ║  • Valid trading account configured                      ║
    ║  • Appropriate risk limits set                           ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
        
        response = input("Start MetaTrader bot? (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y']:
            print("Bot startup cancelled.")
            return
    
    # Get config path from command line or use default
    config_path = "config/metatrader_config.json"
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        config_path = sys.argv[1]
    elif not auto_mode:
        user_path = input("Config file (default: config/metatrader_config.json): ").strip()
        if user_path:
            config_path = user_path
    
    try:
        bot = MetaTraderBot(config_path=config_path)
        bot.start()
        
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        logger.error("Please run setup_metatrader.py first")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)


if __name__ == "__main__":
    main()
