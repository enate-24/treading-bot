"""
Get symbol statistics from MetaTrader 5 for web dashboard
"""
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from collections import defaultdict
import json
import sys

def get_symbol_statistics():
    """Get trading statistics by symbol"""
    
    # Initialize MT5
    if not mt5.initialize():
        return None
    
    try:
        # Get deals from last 30 days
        from_date = datetime.now() - timedelta(days=30)
        deals = mt5.history_deals_get(from_date, datetime.now())
        
        if deals is None or len(deals) == 0:
            return {"symbols": []}
        
        # Analyze deals by symbol
        symbol_stats = defaultdict(lambda: {
            'symbol': '',
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'total_profit': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'profit_factor': 0
        })
        
        for deal in deals:
            # Only count OUT deals (position closures)
            if deal.entry == 1:  # 1 = OUT (exit)
                symbol = deal.symbol
                profit = deal.profit + deal.commission + deal.swap
                
                symbol_stats[symbol]['symbol'] = symbol
                symbol_stats[symbol]['total_trades'] += 1
                symbol_stats[symbol]['total_profit'] += profit
                
                if profit > 0.01:  # Win
                    symbol_stats[symbol]['wins'] += 1
                elif profit < -0.01:  # Loss
                    symbol_stats[symbol]['losses'] += 1
        
        # Calculate statistics
        result_symbols = []
        for symbol, stats in symbol_stats.items():
            if stats['total_trades'] > 0:
                stats['win_rate'] = (stats['wins'] / stats['total_trades']) * 100
                
                # Calculate average win/loss
                winning_deals = [d for d in deals if d.symbol == symbol and d.entry == 1 and (d.profit + d.commission + d.swap) > 0.01]
                losing_deals = [d for d in deals if d.symbol == symbol and d.entry == 1 and (d.profit + d.commission + d.swap) < -0.01]
                
                if winning_deals:
                    stats['avg_win'] = sum([d.profit + d.commission + d.swap for d in winning_deals]) / len(winning_deals)
                
                if losing_deals:
                    stats['avg_loss'] = sum([d.profit + d.commission + d.swap for d in losing_deals]) / len(losing_deals)
                
                # Calculate profit factor
                total_wins = sum([d.profit + d.commission + d.swap for d in winning_deals])
                total_losses = abs(sum([d.profit + d.commission + d.swap for d in losing_deals]))
                
                if total_losses > 0:
                    stats['profit_factor'] = total_wins / total_losses
                else:
                    stats['profit_factor'] = total_wins if total_wins > 0 else 0
                
                result_symbols.append(stats)
        
        # Sort by total profit (descending)
        result_symbols.sort(key=lambda x: x['total_profit'], reverse=True)
        
        return {"symbols": result_symbols}
        
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    stats = get_symbol_statistics()
    if stats:
        print(json.dumps(stats))
    else:
        print(json.dumps({"symbols": []}))
