"""
Fixed Trading Bot - Based on diagnosis results
Only trades profitable symbols with strict filters
"""
import MetaTrader5 as mt5
import logging
import time
import json
from datetime import datetime
from typing import Dict, Optional

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
from trading_bot.strategies.conservative_strategy import ConservativeStrategy
from trading_bot.models.core import MarketData, OHLCV, TradingSignal
from trading_bot.models.enums import SignalDirection, OrderSide

class FixedBot:
    """Fixed trading bot with conservative strategy"""
    
    def __init__(self, config_path: str = "config/metatrader_config_fixed.json"):
        """Initialize the fixed bot"""
        logger.info("=" * 60)
        logger.info("Initializing FIXED Trading Bot")
        logger.info("=" * 60)
        
        # Load configuration
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
        
        from types import SimpleNamespace
        self.config = json.loads(json.dumps(config_dict), object_hook=lambda d: SimpleNamespace(**d))
        
        # Initialize components
        self.mt_connector = MetaTraderConnector(
            account=self.config.metatrader.account,
            password=self.config.metatrader.password,
            server=self.config.metatrader.server,
            mt_version=self.config.metatrader.mt_version
        )
        
        # Initialize conservative strategy
        self.strategy = ConservativeStrategy(
            config_dict.get('strategy_parameters', {}).get('enhanced_hft', {})
        )
        
        self.signal_generator = SignalGenerator()
        self.signal_generator.set_strategy(self.strategy)
        
        # State tracking
        self.running = False
        self.open_positions: Dict[str, dict] = {}
        self.signal_count = 0
        self.trade_count = 0
        
        logger.info("[OK] Conservative Strategy loaded")
        logger.info(f"[OK] Trading symbols: {self.config.trading.symbols}")
        logger.info(f"[OK] Min confidence: {self.config.trading.min_confidence}")
        logger.info(f"[OK] Risk/Reward: {self.config.strategy_parameters.enhanced_hft.min_risk_reward_ratio}:1")
    
    def process_symbol(self, symbol: str, timeframe: str):
        """Process a single symbol"""
        try:
            # Check if we should trade now
            if not self.strategy.should_trade_now():
                return
            
            # Check position limit
            if len(self.open_positions) >= self.config.trading.max_positions:
                return
            
            # Check if already have position in this symbol
            if symbol in self.open_positions:
                return
            
            # Get market data
            bars = self.mt_connector.get_market_data(symbol, timeframe, bars=100)
            if not bars:
                return
            
            ohlcv_list = [
                OHLCV(
                    open=float(bar['open']),
                    high=float(bar['high']),
                    low=float(bar['low']),
                    close=float(bar['close']),
                    volume=float(bar['volume'])
                )
                for bar in bars
            ]
            
            # Use the latest bar for MarketData
            latest_bar = OHLCV(
                open=float(bars[-1]['open']),
                high=float(bars[-1]['high']),
                low=float(bars[-1]['low']),
                close=float(bars[-1]['close']),
                volume=float(bars[-1]['volume'])
            )
            
            market_data = MarketData(
                symbol=symbol,
                timestamp=bars[-1]['timestamp'] if bars else datetime.now(),
                ohlcv=latest_bar,
                indicators={}
            )
            
            # Store the full OHLCV list in metadata for strategy to use
            market_data.ohlcv_list = ohlcv_list
            
            # Generate signal
            signal = self.signal_generator.analyze_market_data(market_data)
            
            if signal and signal.confidence >= self.config.trading.min_confidence:
                self.signal_count += 1
                
                logger.info(f"[SIGNAL] #{self.signal_count}: {signal.direction.value} {symbol}")
                logger.info(f"   Confidence: {signal.confidence:.2%}")
                logger.info(f"   Metadata: {signal.metadata}")
                
                # Calculate position size (fixed 0.01 for safety)
                volume = 0.01
                
                # Get prices from signal metadata
                current_price = signal.metadata.get('entry_price')
                stop_loss = signal.metadata.get('stop_loss')
                take_profit = signal.metadata.get('take_profit')
                
                # Place order
                order_type = OrderSide.BUY if signal.direction == SignalDirection.BUY else OrderSide.SELL
                
                logger.info(f"[ORDER] Placing {order_type.value} order: {volume} lots {symbol}")
                logger.info(f"   Entry: {current_price:.5f}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}")
                
                order_result = self.mt_connector.place_order(
                    symbol=symbol,
                    order_type=order_type,
                    volume=volume,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                
                if order_result:
                    self.trade_count += 1
                    logger.info(f"[SUCCESS] Trade #{self.trade_count} placed")
                    
                    self.open_positions[symbol] = {
                        'order_id': order_result['order_id'],
                        'direction': signal.direction,
                        'volume': volume,
                        'entry_price': current_price,
                        'sl': stop_loss,
                        'tp': take_profit,
                        'timestamp': datetime.now(),
                        'confidence': signal.confidence
                    }
                else:
                    logger.error(f"[FAILED] Order placement failed")
                    
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}", exc_info=True)
    
    def monitor_positions(self):
        """Monitor open positions"""
        try:
            current_positions = self.mt_connector.get_positions()
            
            if not current_positions:
                # All positions closed
                if self.open_positions:
                    for symbol in list(self.open_positions.keys()):
                        logger.info(f"Position closed: {symbol}")
                        # Record result (we don't have exact profit here)
                        self.open_positions.pop(symbol)
                return
            
            # Update open positions
            current_symbols = {pos['symbol'] for pos in current_positions}
            
            # Check for closed positions
            closed_symbols = set(self.open_positions.keys()) - current_symbols
            for symbol in closed_symbols:
                logger.info(f"Position closed: {symbol}")
                self.open_positions.pop(symbol)
                
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
    
    def log_status(self):
        """Log current status"""
        try:
            account_info = self.mt_connector.get_account_info()
            
            if account_info:
                logger.info("=" * 60)
                logger.info("FIXED BOT STATUS")
                logger.info("-" * 60)
                logger.info(f"Balance:          ${account_info['balance']:.2f} USD")
                logger.info(f"Equity:           ${account_info['equity']:.2f}")
                logger.info(f"Open Positions:   {len(self.open_positions)}")
                logger.info(f"Signals Generated: {self.signal_count}")
                logger.info(f"Trades Placed:    {self.trade_count}")
                logger.info(f"Daily Loss:       ${self.strategy._state['daily_loss']:.2f}")
                logger.info(f"Consecutive Losses: {self.strategy._state['consecutive_losses']}")
                logger.info("=" * 60)
        except Exception as e:
            logger.error(f"Error logging status: {e}")
    
    def start(self) -> None:
        """Start the fixed trading bot"""
        try:
            logger.info("=" * 60)
            logger.info("FIXED TRADING BOT")
            logger.info("=" * 60)
            logger.info("Improvements:")
            logger.info("  • Only profitable symbols (EURJPYm, GBPJPYm)")
            logger.info("  • Avoids losing hours")
            logger.info("  • 75% minimum confidence")
            logger.info("  • 2:1 Risk/Reward ratio")
            logger.info("  • Max 3 consecutive losses protection")
            logger.info("  • $0.50 daily loss limit")
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
                logger.info(f"Balance: ${account_info['balance']:.2f} USD")
            
            logger.info("=" * 60)
            logger.info("[START] Fixed Bot Started")
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
                    
                    # Sleep
                    time.sleep(5)
                    
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
        """Stop the trading bot"""
        logger.info("=" * 60)
        logger.info("Stopping Fixed Bot...")
        logger.info("=" * 60)
        
        self.running = False
        self.log_status()
        self.mt_connector.disconnect()
        
        logger.info("[OK] Bot stopped successfully")

def main():
    """Main entry point"""
    import sys
    
    auto_mode = '--auto' in sys.argv or '-y' in sys.argv
    
    if not auto_mode:
        print("\n")
        print("╔" + "=" * 58 + "╗")
        print("║" + " " * 15 + "FIXED TRADING BOT" + " " * 26 + "║")
        print("╚" + "=" * 58 + "╝")
        print()
        print("Fixed Issues:")
        print("  [OK] Only trades profitable symbols (EURJPYm, GBPJPYm)")
        print("  [OK] Avoids losing hours (3, 12, 13, 16, 17, 21, 22, 23 GMT)")
        print("  [OK] 75% minimum confidence (was 15%)")
        print("  [OK] 2:1 Risk/Reward ratio (was 1.5:1)")
        print("  [OK] Max 3 consecutive losses protection")
        print("  [OK] $0.50 daily loss limit")
        print()
        
        response = input("Start fixed bot? (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y']:
            print("\n[CANCELLED] Bot start cancelled")
            return
    
    print("\n[START] Starting fixed bot...\n")
    
    bot = FixedBot()
    bot.start()

if __name__ == "__main__":
    main()
