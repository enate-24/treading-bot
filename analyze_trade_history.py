"""
Analyze complete MetaTrader 5 trade history
"""
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from collections import defaultdict

# Initialize MT5
if not mt5.initialize():
    print(f"ERROR: MT5 initialization failed: {mt5.last_error()}")
    exit()

print("=" * 70)
print("METATRADER 5 TRADE HISTORY ANALYSIS")
print("=" * 70)

# Get account info
account_info = mt5.account_info()
if account_info:
    print(f"Account: {account_info.login}")
    print(f"Current Balance: ${account_info.balance:.2f} USD")
    print(f"Current Equity: ${account_info.equity:.2f} USD")
    print("=" * 70)

# Get all deals from the beginning
# Try to get deals from last 30 days
from_date = datetime.now() - timedelta(days=30)
deals = mt5.history_deals_get(from_date, datetime.now())

if deals is None or len(deals) == 0:
    print("No trade history found")
    mt5.shutdown()
    exit()

print(f"\nTotal Deals Found: {len(deals)}")
print("-" * 70)

# Analyze deals
winning_trades = []
losing_trades = []
breakeven_trades = []
total_profit = 0
total_loss = 0

# Group deals by symbol
symbol_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'profit': 0, 'loss': 0})

for deal in deals:
    # Only count OUT deals (position closures)
    if deal.entry == 1:  # 1 = OUT (exit), 0 = IN (entry)
        profit = deal.profit + deal.commission + deal.swap
        total_profit += profit
        
        if profit > 0.01:  # Winning trade
            winning_trades.append(deal)
            symbol_stats[deal.symbol]['wins'] += 1
            symbol_stats[deal.symbol]['profit'] += profit
            total_profit += profit
        elif profit < -0.01:  # Losing trade
            losing_trades.append(deal)
            symbol_stats[deal.symbol]['losses'] += 1
            symbol_stats[deal.symbol]['loss'] += profit
            total_loss += profit
        else:  # Breakeven
            breakeven_trades.append(deal)

# Calculate statistics
total_closed_trades = len(winning_trades) + len(losing_trades) + len(breakeven_trades)
win_rate = (len(winning_trades) / total_closed_trades * 100) if total_closed_trades > 0 else 0
loss_rate = (len(losing_trades) / total_closed_trades * 100) if total_closed_trades > 0 else 0

avg_win = (sum([d.profit + d.commission + d.swap for d in winning_trades]) / len(winning_trades)) if winning_trades else 0
avg_loss = (sum([d.profit + d.commission + d.swap for d in losing_trades]) / len(losing_trades)) if losing_trades else 0

profit_factor = abs(sum([d.profit + d.commission + d.swap for d in winning_trades]) / sum([d.profit + d.commission + d.swap for d in losing_trades])) if losing_trades else 0

print("\nOVERALL STATISTICS:")
print("-" * 70)
print(f"Total Closed Trades:    {total_closed_trades}")
print(f"Winning Trades:         {len(winning_trades)} ({win_rate:.1f}%)")
print(f"Losing Trades:          {len(losing_trades)} ({loss_rate:.1f}%)")
print(f"Breakeven Trades:       {len(breakeven_trades)}")
print()
print(f"Total Profit:           ${total_profit:.2f} USD")
print(f"Average Win:            ${avg_win:.2f} USD")
print(f"Average Loss:           ${avg_loss:.2f} USD")
print(f"Profit Factor:          {profit_factor:.2f}")
print(f"Risk/Reward Ratio:      {abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "Risk/Reward Ratio:      N/A")

# Show recent trades
print("\n" + "=" * 70)
print("RECENT TRADES (Last 20):")
print("=" * 70)
recent_deals = [d for d in deals if d.entry == 1][-20:]

for deal in recent_deals:
    profit = deal.profit + deal.commission + deal.swap
    status = "WIN" if profit > 0 else "LOSS" if profit < 0 else "BE"
    deal_time = datetime.fromtimestamp(deal.time)
    
    print(f"{deal_time.strftime('%Y-%m-%d %H:%M:%S')} | {deal.symbol:10s} | "
          f"{'BUY' if deal.type == 0 else 'SELL':4s} | "
          f"Vol: {deal.volume:.2f} | "
          f"Price: {deal.price:.5f} | "
          f"Profit: ${profit:7.2f} | {status}")

# Show statistics by symbol
print("\n" + "=" * 70)
print("STATISTICS BY SYMBOL:")
print("=" * 70)
for symbol, stats in sorted(symbol_stats.items(), key=lambda x: x[1]['profit'] + x[1]['loss'], reverse=True):
    total_trades = stats['wins'] + stats['losses']
    symbol_win_rate = (stats['wins'] / total_trades * 100) if total_trades > 0 else 0
    total_pnl = stats['profit'] + stats['loss']
    
    print(f"{symbol:10s} | Trades: {total_trades:3d} | "
          f"Wins: {stats['wins']:3d} ({symbol_win_rate:5.1f}%) | "
          f"Losses: {stats['losses']:3d} | "
          f"P&L: ${total_pnl:7.2f}")

# Show today's performance
print("\n" + "=" * 70)
print("TODAY'S PERFORMANCE:")
print("=" * 70)
today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
today_deals = [d for d in deals if d.entry == 1 and datetime.fromtimestamp(d.time) >= today_start]

if today_deals:
    today_wins = [d for d in today_deals if (d.profit + d.commission + d.swap) > 0]
    today_losses = [d for d in today_deals if (d.profit + d.commission + d.swap) < 0]
    today_profit = sum([d.profit + d.commission + d.swap for d in today_deals])
    today_win_rate = (len(today_wins) / len(today_deals) * 100) if today_deals else 0
    
    print(f"Today's Trades:         {len(today_deals)}")
    print(f"Today's Wins:           {len(today_wins)} ({today_win_rate:.1f}%)")
    print(f"Today's Losses:         {len(today_losses)}")
    print(f"Today's Profit:         ${today_profit:.2f} USD")
else:
    print("No trades today")

print("\n" + "=" * 70)
print(f"Analysis completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# Shutdown
mt5.shutdown()
