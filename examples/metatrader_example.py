"""Example of using MetaTrader 4/5 connector."""

import sys
import os
# Add parent directory to path so we can import trading_bot
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from trading_bot.connectors import MetaTraderConnector

# Configure logging
logging.basicConfig(level=logging.INFO)


def main():
    """Demonstrate MetaTrader connector usage."""
    
    print("🔌 MetaTrader Connector Example")
    print("=" * 50)
    
    # Your MetaTrader account credentials
    ACCOUNT = 12345678  # Replace with your account number
    PASSWORD = "your_password"  # Replace with your password
    SERVER = "YourBroker-Demo"  # Replace with your broker's server name
    
    # Create connector
    mt_connector = MetaTraderConnector(
        account=ACCOUNT,
        password=PASSWORD,
        server=SERVER,
        mt_version=5
    )
    
    # Connect to MetaTrader
    if not mt_connector.connect():
        print("❌ Failed to connect to MetaTrader")
        return
    
    try:
        # Get account information
        print("\n📊 Account Information:")
        account_info = mt_connector.get_account_info()
        if account_info:
            print(f"  Balance: {account_info['balance']} {account_info['currency']}")
            print(f"  Equity: {account_info['equity']}")
            print(f"  Free Margin: {account_info['free_margin']}")
            print(f"  Leverage: 1:{account_info['leverage']}")
            print(f"  Server: {account_info['server']}")
        
        # Get available symbols
        print("\n📈 Available Symbols (first 10):")
        symbols = mt_connector.get_symbols()[:10]
        for symbol in symbols:
            print(f"  • {symbol}")
        
        # Get symbol information
        symbol = "EURUSD"
        print(f"\n💱 Symbol Info for {symbol}:")
        symbol_info = mt_connector.get_symbol_info(symbol)
        if symbol_info:
            print(f"  Bid: {symbol_info['bid']}")
            print(f"  Ask: {symbol_info['ask']}")
            print(f"  Spread: {symbol_info['spread']}")
            print(f"  Min Volume: {symbol_info['volume_min']}")
            print(f"  Max Volume: {symbol_info['volume_max']}")
        
        # Get market data
        print(f"\n📉 Market Data for {symbol} (last 5 bars on H1):")
        market_data = mt_connector.get_market_data(symbol, "H1", bars=5)
        if market_data:
            for bar in market_data[-5:]:
                print(f"  {bar['timestamp']}: O={bar['open']:.5f} H={bar['high']:.5f} "
                      f"L={bar['low']:.5f} C={bar['close']:.5f} V={bar['volume']}")
        
        # Get open positions
        print("\n📋 Open Positions:")
        positions = mt_connector.get_positions()
        if positions:
            for pos in positions:
                print(f"  Ticket: {pos['ticket']}, {pos['type']} {pos['volume']} {pos['symbol']} "
                      f"@ {pos['price_open']}, Profit: {pos['profit']}")
        else:
            print("  No open positions")
        
        # Example: Place a market order (COMMENTED OUT FOR SAFETY)
        # Uncomment and modify to place real orders
        """
        print("\n🛒 Placing Order:")
        order_result = mt_connector.place_order(
            symbol="EURUSD",
            order_type="BUY",
            volume=0.01,  # 0.01 lots (micro lot)
            sl=1.0500,    # Stop loss
            tp=1.0700,    # Take profit
            comment="Test order"
        )
        if order_result:
            print(f"  ✅ Order placed: {order_result}")
        """
        
        print("\n✅ MetaTrader connector working successfully!")
        
    finally:
        # Disconnect
        mt_connector.disconnect()
        print("\n👋 Disconnected from MetaTrader")


if __name__ == "__main__":
    main()
