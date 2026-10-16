"""
Ultra Aggressive HFT Bot - Will generate many signals for testing.
WARNING: This is for testing only! Use with caution on real accounts.
"""
import MetaTrader5 as mt5
import logging
import time
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
        logging.FileHandler('metatrader_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import bot components
from trading_bot.configuration_manager import ConfigurationManager
from trading_bot.connectors.metatrader_connector import MetaTraderConnector
from trading_bot.signal_generator import SignalGenerator
from trading_bot.strategies.hft_strategy import HFTStrategy
from trading_bot.performance_monitor import PerformanceMonitor
from trading_bot.models.market_data import MarketData, OHLCV
from trading_bot.models.signal import SignalDirection
from trading_bot.models.trade import ExecutedTrade, OrderSide

class UltraAggressiveBot:
    """Ultra aggressive HFT bot for testing."""
    
    def __init__(self, config_path: str = "config/metatrader_config_ultra_aggressive.json"):
        """Initialize the bot."""
        logger.info("Initializing Ultra Aggressive HFT Bot")
        
        # Load configuration
        self.config_manager = ConfigurationManager(config_path)
        self.config = self.config_manager.config
        
        # Initialize components
        self.mt_connector = MetaTraderConnector(self.config)
        self.hft_strategy = HFTStrategy(self.config.strategy_parameters.get('hft', {}))
        self.signal_generator = SignalGenerator(self.config, self.hft_strategy)
        self.performance_monitor = PerformanceMonitor(self.config)
        
        # Trading state
        self.running = False
        self.open_positions: Dict[str, dict] = {}
        self.signal_count = 0
        self.trade_count = 0
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def calculate_position_size(self, symbol: str) -> float:
        """Calculate position size."""
        account_info = self.mt_connector.get_account_info()
        if not account_info:
            return 0.01
        
        balance = account_info['balance']
        risk_amount = balance * self.config.risk_management.risk_per_trade
        
        # Use minimum lot size for ultra aggressive testing
        return 0.01
    
    def process_symbol(self, symbol: str, timeframe: str) -> None:
        """Process trading logic for a symbol."""
        try:
            # Get market data
            market_data_raw = self.mt_connector.get_market_data(symbol, timeframe, bars=100)
            
            if not market_data_raw or len(market_data_raw) == 0:
                return
            
            latest_bar = market_data_raw[-1]
            closes = [bar['close'] for bar in market_data_raw]
            
            # Calculate simple indicators
            sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else closes[-1]
            sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else closes[-1]
            
            indicators = {
                'sma_20': sma_20,
                'sma_50': sma_50,
                'rsi': 50.0  # Neutral RSI
            }
            
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
                self.signal_count += 1
                logger.info(f"📊 Signal #{self.signal_count}: {signal.direction.value} {symbol}")
                logger.info(f"   Strength: {signal.strength:.2f}, Confidence: {signal.confidence:.2f}")
                
                # Check position limits
                max_positions = self.config.risk_management.max_positions
                
                if len(self.open_positions) >= max_positions:
                    logger.warning(f"⚠️  Max positions reached ({max_positions})")
                    return
                
                if symbol in self.open_positions:
                    logger.info(f"ℹ️  Already have position in {symbol}")
                    return
                
                # Calculate position size
                volume = self.calculate_position_size(symbol)
                
                # Calculate SL/TP
                current_price = float(latest_bar['close'])
                stop_loss_pct = 0.0015  # 0.15%
                profit_target_pct = 0.002  # 0.2%
                
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
                logger.info(f"   Entry: {current_price:.5f}, SL: {sl:.5f}, TP: {tp:.5f}")
                
                order_result = self.mt_connector.place_order(
                    symbol=symbol,
                    order_type=order_type,
                    volume=volume,
                    sl=sl,
                    tp=tp,
                    comment="UltraAggressive"
                )
                
                if order_result:
                    self.trade_count += 1
                    logger.info(f"✅ Trade #{self.trade_count} placed: Order {order_result['order_id']}")
                    
                    self.open_positions[symbol] = {
                        'order_id': order_result['order_id'],
                        'direction': signal.direction,
                        'volume': volume,
                        'entry_price': order_result['price'],
                        'sl': sl,
                        'tp': tp,
                        'timestamp': datetime.now()
                    }
                else:
                    logger.error(f"❌ Failed to place order for {symbol}")
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}", exc_info=True)
    
    def monitor_positions(self) -> None:
        """Monitor and update open positions."""
        try:
            positions = self.mt_connector.get_open_positions()
            
            # Update our tracking
            current_symbols = set()
            if positions:
                for pos in positions:
                    current_symbols.add(pos['symbol'])
            
            # Remove closed positions from tracking
            closed_symbols = set(self.open_positions.keys()) - current_symbols
            for symbol in closed_symbols:
                logger.info(f"📍 Position closed: {symbol}")
                del self.open_positions[symbol]
            
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
    
    def log_status(self) -> None:
        """Log current bot status."""
        try:
            account_info = self.mt_connector.get_account_info()
            if account_info:
                logger.info("=" * 60)
                logger.info("BOT STATUS")
                logger.info("-" * 60)
                logger.info(f"Balance:          {account_info['balance']:.2f} USD")
                logger.info(f"Equity:           {account_info['equity']:.2f}")
                logger.info(f"Free Margin:      {account_info['free_margin']:.2f}")
                logger.info(f"Open Positions:   {len(self.open_positions)}")
                logger.info(f"Signals Generated: {self.signal_count}")
                logger.info(f"Trades Placed:    {self.trade_count}")
                logger.info("=" * 60)
        except Exception as e:
            logger.error(f"Error logging status: {e}")
    
    def start(self) -> None:
        """Start the trading bot."""
        try:
            logger.info("=" * 60)
            logger.info("ULTRA AGGRESSIVE HFT BOT")
            logger.info("=" * 60)
            logger.info("⚠️  WARNING: This bot will generate MANY signals!")
            logger.info("⚠️  Use only for testing with small amounts!")
            logger.info("=" * 60)
            
            # Connect to MetaTrader
            if not self.mt_connector.connect():
                logger.error("Failed to connect to MetaTrader")
                return
            
            logger.info("✅ Connected to MetaTrader 5")
            
            # Get account info
            account_info = self.mt_connector.get_account_info()
            if account_info:
                logger.info(f"Account: {account_info['login']}")
                logger.info(f"Balance: {account_info['balance']} USD")
                logger.info(f"Leverage: 1:{account_info['leverage']}")
            
            logger.info("=" * 60)
            logger.info("🚀 Ultra Aggressive Bot Started")
            logger.info("Press Ctrl+C to stop")
            logger.info("=" * 60)
            
            self.running = True
            last_status_time = datetime.now()
            
            # Main trading loop
            while self.running:
                try:
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
                    
                    # Sleep briefly (ultra aggressive = fast loop)
                    time.sleep(2)
                    
                except KeyboardInterrupt:
                    logger.info("\n⚠️  Keyboard interrupt received")
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
        logger.info("Stopping Ultra Aggressive Bot...")
        logger.info("=" * 60)
        
        self.running = False
        
        # Final status
        self.log_status()
        
        # Disconnect
        self.mt_connector.disconnect()
        
        logger.info("✅ Bot stopped successfully")
        logger.info(f"Total Signals: {self.signal_count}")
        logger.info(f"Total Trades: {self.trade_count}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"\n⚠️  Received signal {signum}")
        self.stop()
        sys.exit(0)

def main():
    """Main entry point."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "ULTRA AGGRESSIVE HFT BOT" + " " * 24 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    print("⚠️  WARNING: This bot uses VERY aggressive parameters!")
    print("⚠️  It will generate MANY trading signals!")
    print("⚠️  Use only for TESTING with small amounts!")
    print()
    print("Features:")
    print("  • Min confidence: 5% (very low)")
    print("  • Max positions: 10")
    print("  • Fast execution: 2-second loop")
    print("  • All sessions enabled")
    print()
    
    response = input("Start ultra aggressive bot? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("\n❌ Bot start cancelled")
        return
    
    print("\n🚀 Starting bot...\n")
    
    bot = UltraAggressiveBot()
    bot.start()

if __name__ == "__main__":
    main()
