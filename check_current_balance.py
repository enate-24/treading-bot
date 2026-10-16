"""
Check current MetaTrader 5 balance
"""
import MetaTrader5 as mt5
from datetime import datetime

# Initialize MT5
if not mt5.initialize():
    print(f"ERROR: MT5 initialization failed: {mt5.last_error()}")
    exit()

# Get account info
account_info = mt5.account_info()

if account_info is None:
    print(f"ERROR: Failed to get account info: {mt5.last_error()}")
    mt5.shutdown()
    exit()

# Display account information
print("=" * 60)
print("METATRADER 5 ACCOUNT INFORMATION")
print("=" * 60)
print(f"Account Number:  {account_info.login}")
print(f"Server:          {account_info.server}")
print(f"Balance:         ${account_info.balance:.2f} USD")
print(f"Equity:          ${account_info.equity:.2f} USD")
print(f"Margin:          ${account_info.margin:.2f} USD")
print(f"Free Margin:     ${account_info.margin_free:.2f} USD")
print(f"Margin Level:    {account_info.margin_level:.2f}%" if account_info.margin > 0 else "Margin Level:    N/A")
print(f"Profit:          ${account_info.profit:.2f} USD")
print(f"Leverage:        1:{account_info.leverage}")
print(f"Currency:        {account_info.currency}")
print("=" * 60)

# Get open positions
positions = mt5.positions_get()
if positions is None:
    print(f"No positions found or error: {mt5.last_error()}")
    positions = []

print(f"\nOpen Positions:  {len(positions)}")
if len(positions) > 0:
    print("-" * 60)
    for pos in positions:
        print(f"  Ticket:   {pos.ticket}")
        print(f"  Symbol:   {pos.symbol}")
        print(f"  Type:     {'BUY' if pos.type == 0 else 'SELL'}")
        print(f"  Volume:   {pos.volume}")
        print(f"  Price:    {pos.price_open:.5f}")
        print(f"  Current:  {pos.price_current:.5f}")
        print(f"  Profit:   ${pos.profit:.2f} USD")
        print(f"  SL:       {pos.sl:.5f}")
        print(f"  TP:       {pos.tp:.5f}")
        print("-" * 60)

# Get today's deals
from datetime import datetime, timedelta
today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
deals = mt5.history_deals_get(today_start, datetime.now())

if deals is None:
    print(f"\nNo deals found today")
else:
    print(f"\nToday's Deals:   {len(deals)}")
    total_profit = sum([deal.profit for deal in deals if deal.entry == 1])  # Only OUT deals
    print(f"Today's Profit:  ${total_profit:.2f} USD")

print("\n" + "=" * 60)
print(f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# Shutdown
mt5.shutdown()
