"""
Comprehensive diagnosis of trading problems
"""
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

def diagnose_problems():
    """Identify specific problems causing losses"""
    
    if not mt5.initialize():
        print("ERROR: MT5 initialization failed")
        return
    
    try:
        print("=" * 80)
        print("TRADING PROBLEMS DIAGNOSIS")
        print("=" * 80)
        
        # Get deals
        from_date = datetime.now() - timedelta(days=30)
        deals = mt5.history_deals_get(from_date, datetime.now())
        
        if not deals or len(deals) == 0:
            print("No trading history found")
            return
        
        # Analyze closed trades
        closed_trades = []
        for deal in deals:
            if deal.entry == 1:  # OUT (exit)
                profit = deal.profit + deal.commission + deal.swap
                closed_trades.append({
                    'time': deal.time,
                    'symbol': deal.symbol,
                    'profit': profit,
                    'volume': deal.volume,
                    'type': 'BUY' if deal.type == 0 else 'SELL',
                    'price': deal.price
                })
        
        # Sort by time
        closed_trades.sort(key=lambda x: x['time'])
        
        # PROBLEM 1: Win Rate Analysis
        print("\n1. WIN RATE ANALYSIS")
        print("-" * 80)
        winning = [t for t in closed_trades if t['profit'] > 0]
        losing = [t for t in closed_trades if t['profit'] < 0]
        win_rate = len(winning) / len(closed_trades) * 100 if closed_trades else 0
        
        print(f"Total Trades: {len(closed_trades)}")
        print(f"Winning: {len(winning)} ({win_rate:.1f}%)")
        print(f"Losing: {len(losing)} ({100-win_rate:.1f}%)")
        print(f"\n❌ PROBLEM: Win rate is {win_rate:.1f}% (need 50%+ for profitability)")
        print(f"   You're losing {100-win_rate:.1f}% of trades - strategy is not working!")
        
        # PROBLEM 2: Risk/Reward Ratio
        print("\n2. RISK/REWARD RATIO ANALYSIS")
        print("-" * 80)
        avg_win = sum([t['profit'] for t in winning]) / len(winning) if winning else 0
        avg_loss = abs(sum([t['profit'] for t in losing]) / len(losing)) if losing else 0
        rr_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        print(f"Average Win: ${avg_win:.2f}")
        print(f"Average Loss: ${avg_loss:.2f}")
        print(f"Risk/Reward Ratio: {rr_ratio:.2f}:1")
        
        if rr_ratio < 1.5:
            print(f"\n❌ PROBLEM: R:R ratio is {rr_ratio:.2f}:1 (need 1.5:1 minimum)")
            print(f"   Your wins are too small compared to losses!")
        
        # PROBLEM 3: Symbol Performance
        print("\n3. SYMBOL PERFORMANCE ANALYSIS")
        print("-" * 80)
        symbol_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'profit': 0})
        
        for trade in closed_trades:
            symbol_stats[trade['symbol']]['profit'] += trade['profit']
            if trade['profit'] > 0:
                symbol_stats[trade['symbol']]['wins'] += 1
            else:
                symbol_stats[trade['symbol']]['losses'] += 1
        
        print(f"{'Symbol':<12} {'Trades':<8} {'Win Rate':<12} {'Total P&L':<12} {'Status'}")
        print("-" * 80)
        
        bad_symbols = []
        for symbol, stats in sorted(symbol_stats.items(), key=lambda x: x[1]['profit']):
            total = stats['wins'] + stats['losses']
            wr = stats['wins'] / total * 100 if total > 0 else 0
            status = "✓ GOOD" if stats['profit'] > 0 and wr >= 40 else "✗ BAD"
            
            print(f"{symbol:<12} {total:<8} {wr:>5.1f}%      ${stats['profit']:>7.2f}     {status}")
            
            if stats['profit'] < 0 or wr < 30:
                bad_symbols.append(symbol)
        
        if bad_symbols:
            print(f"\n❌ PROBLEM: These symbols are losing money:")
            for sym in bad_symbols:
                print(f"   - {sym}: Remove from trading!")
        
        # PROBLEM 4: Trade Timing
        print("\n4. TRADE TIMING ANALYSIS")
        print("-" * 80)
        
        hour_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'profit': 0})
        for trade in closed_trades:
            hour = datetime.fromtimestamp(trade['time']).hour
            hour_stats[hour]['profit'] += trade['profit']
            if trade['profit'] > 0:
                hour_stats[hour]['wins'] += 1
            else:
                hour_stats[hour]['losses'] += 1
        
        print(f"{'Hour (GMT)':<12} {'Trades':<8} {'Win Rate':<12} {'Total P&L':<12} {'Status'}")
        print("-" * 80)
        
        bad_hours = []
        for hour in sorted(hour_stats.keys()):
            stats = hour_stats[hour]
            total = stats['wins'] + stats['losses']
            wr = stats['wins'] / total * 100 if total > 0 else 0
            status = "✓ GOOD" if stats['profit'] > 0 else "✗ BAD"
            
            print(f"{hour:02d}:00        {total:<8} {wr:>5.1f}%      ${stats['profit']:>7.2f}     {status}")
            
            if stats['profit'] < -0.5:
                bad_hours.append(hour)
        
        if bad_hours:
            print(f"\n❌ PROBLEM: Trading during these hours loses money:")
            for h in bad_hours:
                print(f"   - {h:02d}:00 GMT: Avoid trading!")
        
        # PROBLEM 5: Consecutive Losses
        print("\n5. CONSECUTIVE LOSSES ANALYSIS")
        print("-" * 80)
        
        max_consecutive_losses = 0
        current_losses = 0
        
        for trade in closed_trades:
            if trade['profit'] < 0:
                current_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, current_losses)
            else:
                current_losses = 0
        
        print(f"Max Consecutive Losses: {max_consecutive_losses}")
        
        if max_consecutive_losses > 5:
            print(f"\n❌ PROBLEM: {max_consecutive_losses} consecutive losses!")
            print(f"   Strategy has no stop mechanism for losing streaks")
        
        # PROBLEM 6: Position Sizing
        print("\n6. POSITION SIZING ANALYSIS")
        print("-" * 80)
        
        volumes = [t['volume'] for t in closed_trades]
        avg_volume = np.mean(volumes)
        
        print(f"Average Position Size: {avg_volume:.2f} lots")
        print(f"Min: {min(volumes):.2f} lots")
        print(f"Max: {max(volumes):.2f} lots")
        
        # Check if position sizing is consistent
        if max(volumes) == min(volumes):
            print(f"\n⚠️  WARNING: Fixed position size (no dynamic sizing)")
            print(f"   Not adjusting for confidence or volatility")
        
        # PROBLEM 7: Stop Loss Effectiveness
        print("\n7. STOP LOSS ANALYSIS")
        print("-" * 80)
        
        large_losses = [t for t in losing if t['profit'] < -0.5]
        print(f"Trades with loss > $0.50: {len(large_losses)}")
        
        if large_losses:
            print(f"\n❌ PROBLEM: {len(large_losses)} trades with large losses")
            print(f"   Stop losses may be too wide or not working")
            print(f"   Largest loss: ${min([t['profit'] for t in losing]):.2f}")
        
        # PROBLEM 8: Profit Factor
        print("\n8. PROFIT FACTOR ANALYSIS")
        print("-" * 80)
        
        total_wins = sum([t['profit'] for t in winning])
        total_losses = abs(sum([t['profit'] for t in losing]))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        print(f"Total Wins: ${total_wins:.2f}")
        print(f"Total Losses: ${total_losses:.2f}")
        print(f"Profit Factor: {profit_factor:.2f}")
        
        if profit_factor < 1.0:
            print(f"\n❌ CRITICAL PROBLEM: Profit factor is {profit_factor:.2f}")
            print(f"   You lose ${1/profit_factor:.2f} for every $1 you make!")
            print(f"   Strategy is fundamentally unprofitable")
        
        # PROBLEM 9: Indicator Effectiveness
        print("\n9. STRATEGY EFFECTIVENESS")
        print("-" * 80)
        
        # Check if enhanced strategy is actually being used
        recent_trades = closed_trades[-10:]
        recent_win_rate = len([t for t in recent_trades if t['profit'] > 0]) / len(recent_trades) * 100
        
        print(f"Recent 10 trades win rate: {recent_win_rate:.1f}%")
        
        if recent_win_rate < 30:
            print(f"\n❌ PROBLEM: Recent performance is terrible ({recent_win_rate:.1f}%)")
            print(f"   Enhanced strategy with indicators is NOT working")
            print(f"   Indicators may be giving false signals")
        
        # SUMMARY
        print("\n" + "=" * 80)
        print("SUMMARY OF PROBLEMS")
        print("=" * 80)
        
        problems = []
        
        if win_rate < 40:
            problems.append(f"1. Win rate too low ({win_rate:.1f}%) - Strategy not working")
        
        if rr_ratio < 1.5:
            problems.append(f"2. Poor Risk/Reward ({rr_ratio:.2f}:1) - Wins too small")
        
        if bad_symbols:
            problems.append(f"3. Losing symbols: {', '.join(bad_symbols)}")
        
        if bad_hours:
            problems.append(f"4. Bad trading hours: {', '.join([f'{h:02d}:00' for h in bad_hours])}")
        
        if max_consecutive_losses > 5:
            problems.append(f"5. No protection against losing streaks ({max_consecutive_losses} consecutive)")
        
        if large_losses:
            problems.append(f"6. Stop losses too wide ({len(large_losses)} large losses)")
        
        if profit_factor < 1.0:
            problems.append(f"7. Fundamentally unprofitable (PF: {profit_factor:.2f})")
        
        if recent_win_rate < 30:
            problems.append(f"8. Enhanced strategy failing ({recent_win_rate:.1f}% recent win rate)")
        
        print(f"\nTotal Problems Found: {len(problems)}")
        print()
        for problem in problems:
            print(f"❌ {problem}")
        
        # RECOMMENDATIONS
        print("\n" + "=" * 80)
        print("RECOMMENDED FIXES")
        print("=" * 80)
        
        print("\n1. IMMEDIATE ACTIONS:")
        print("   • STOP TRADING NOW - You're losing money fast")
        print("   • Remove losing symbols:", ', '.join(bad_symbols) if bad_symbols else "None")
        print("   • Avoid bad hours:", ', '.join([f'{h:02d}:00' for h in bad_hours]) if bad_hours else "None")
        
        print("\n2. STRATEGY FIXES:")
        print("   • Increase signal confidence threshold (currently too low)")
        print("   • Tighten stop losses (reduce max loss per trade)")
        print("   • Improve entry signals (too many false signals)")
        print("   • Add trend filter (only trade with trend)")
        
        print("\n3. RISK MANAGEMENT:")
        print("   • Reduce position size to 0.01 lots maximum")
        print("   • Set max daily loss limit ($0.50)")
        print("   • Stop after 3 consecutive losses")
        print("   • Increase R:R ratio to 2:1 minimum")
        
        print("\n4. TESTING:")
        print("   • Paper trade for 1 week minimum")
        print("   • Backtest on historical data")
        print("   • Verify win rate >50% before live trading")
        
        print("\n" + "=" * 80)
        
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    diagnose_problems()
