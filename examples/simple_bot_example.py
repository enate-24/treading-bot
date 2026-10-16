"""Simple example showing how the automated trading bot works."""

import sys
import os
# Add parent directory to path so we can import trading_bot
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from decimal import Decimal
from trading_bot.data_handler import DataHandler
from trading_bot.signal_generator import SignalGenerator
from trading_bot.strategies.swing_trading_strategy import SwingTradingStrategy
from trading_bot.portfolio_manager import PortfolioManager
from trading_bot.risk_manager import RiskManager
from trading_bot.models import OrderRequest, OrderSide, OrderType, SignalDirection
import time


def main():
    """Simple bot example - shows the automated trading flow."""
    
    print("=" * 60)
    print("AUTOMATED TRADING BOT - SIMPLE EXAMPLE")
    print("=" * 60)
    print()
    
    # 1. Initialize Portfolio Manager
    print("1. Initializing Portfolio Manager...")
    portfolio_manager = PortfolioManager(
        initial_capital=Decimal('10000'),  # $10,000 starting capital
        max_risk_per_trade=0.02  # 2% risk per trade
    )
    print(f"   ✓ Starting capital: $10,000")
    print()
    
    # 2. Initialize Risk Manager
    print("2. Initializing Risk Manager...")
    risk_manager = RiskManager(
        portfolio_manager=portfolio_manager,
        config={
            'max_risk_per_trade': 0.02,
            'max_portfolio_drawdown': 0.10,
            'daily_loss_limit': 0.05
        }
    )
    print("   ✓ Risk limits configured")
    print()
    
    # 3. Initialize Data Handler
    print("3. Initializing Data Handler...")
    data_handler = DataHandler(max_history_size=1000)
    data_handler.subscribe_to_symbol("BTC/USDT", "1h")
    print("   ✓ Subscribed to BTC/USDT on 1h timeframe")
    print()
    
    # 4. Initialize Signal Generator with Strategy
    print("4. Initializing Signal Generator...")
    signal_generator = SignalGenerator()
    strategy = SwingTradingStrategy()
    signal_generator.set_strategy(strategy)
    print("   ✓ Using Swing Trading Strategy")
    print()
    
    # 5. Define callback for market data
    print("5. Setting up automated trading callback...")
    
    def on_market_data(market_data):
        """This function is called automatically when new market data arrives."""
        
        # Generate trading signal
        signal = signal_generator.analyze_market_data(market_data)
        
        if signal:
            print(f"\n📊 SIGNAL GENERATED!")
            print(f"   Symbol: {signal.symbol}")
            print(f"   Direction: {signal.direction.value}")
            print(f"   Strength: {signal.strength:.2f}")
            print(f"   Confidence: {signal.confidence:.2f}")
            print(f"   Strategy: {signal.strategy}")
            
            # Calculate position size
            position_size = portfolio_manager.calculate_position_size(signal)
            print(f"   Position Size: ${position_size:,.2f}")
            
            # Create order request
            order_request = OrderRequest(
                symbol=signal.symbol,
                side=OrderSide.BUY if signal.direction == SignalDirection.BUY else OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=position_size / market_data.ohlcv.close,
                price=market_data.ohlcv.close,
                time_in_force=None
            )
            
            # Validate with risk manager
            validation = risk_manager.validate_trade(order_request)
            
            if validation.approved:
                print(f"\n✅ TRADE APPROVED!")
                print(f"   Action: {order_request.side.value}")
                print(f"   Quantity: {order_request.quantity:.4f}")
                print(f"   Price: ${order_request.price:,.2f}")
                print(f"\n   → In production, this order would be sent to the exchange")
            else:
                print(f"\n❌ TRADE REJECTED: {validation.reason}")
        
        # Show portfolio status
        metrics = portfolio_manager.get_portfolio_metrics()
        print(f"\n💼 Portfolio: ${metrics.total_value:,.2f} | "
              f"Available: ${metrics.available_capital:,.2f} | "
              f"Positions: {metrics.positions_count}")
    
    # Register the callback
    data_handler.register_data_callback(on_market_data)
    print("   ✓ Callback registered - bot will trade automatically when signals appear")
    print()
    
    # 6. Start the bot
    print("=" * 60)
    print("BOT IS NOW RUNNING")
    print("=" * 60)
    print()
    print("The bot is now:")
    print("  • Monitoring BTC/USDT market data")
    print("  • Analyzing with Swing Trading Strategy")
    print("  • Will automatically execute trades when signals appear")
    print("  • All trades validated by risk manager")
    print()
    print("Press Ctrl+C to stop...")
    print()
    
    try:
        # Keep running (in production, this would run indefinitely)
        # For this example, we'll run for 30 seconds
        for i in range(30):
            time.sleep(1)
            if i % 10 == 0:
                print(f"⏱️  Bot running... ({i}s)")
        
        print("\n✓ Example completed")
        
    except KeyboardInterrupt:
        print("\n\n⏸️  Bot stopped by user")
    
    finally:
        data_handler.stop()
        print("\n✓ Data handler stopped")
        print("\n" + "=" * 60)
        print("EXAMPLE FINISHED")
        print("=" * 60)
        print()
        print("In production mode (run_trading_bot.py):")
        print("  • Bot runs 24/7 continuously")
        print("  • Connects to real exchanges")
        print("  • Executes actual trades")
        print("  • Manages real positions")
        print("  • Tracks real performance")


if __name__ == "__main__":
    main()
