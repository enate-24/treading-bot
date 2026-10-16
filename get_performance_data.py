"""
Get comprehensive performance data from MetaTrader 5
"""
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from collections import defaultdict
import json
import sys
import numpy as np

def calculate_performance_metrics():
    """Calculate comprehensive performance metrics"""
    
    # Initialize MT5
    if not mt5.initialize():
        return None
    
    try:
        # Get account info
        account_info = mt5.account_info()
        if not account_info:
            return None
        
        # Get deals from last 30 days
        from_date = datetime.now() - timedelta(days=30)
        deals = mt5.history_deals_get(from_date, datetime.now())
        
        if deals is None or len(deals) == 0:
            return {
                "account": {
                    "balance": account_info.balance,
                    "equity": account_info.equity,
                    "profit": account_info.profit,
                    "margin": account_info.margin,
                    "margin_free": account_info.margin_free
                },
                "overall": {},
                "hourly": [],
                "daily": [],
                "symbols": [],
                "trades": []
            }
        
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
                    'type': 'BUY' if deal.type == 0 else 'SELL'
                })
        
        # Calculate overall metrics
        total_trades = len(closed_trades)
        winning_trades = [t for t in closed_trades if t['profit'] > 0]
        losing_trades = [t for t in closed_trades if t['profit'] < 0]
        
        total_profit = sum([t['profit'] for t in closed_trades])
        total_wins = sum([t['profit'] for t in winning_trades])
        total_losses = abs(sum([t['profit'] for t in losing_trades]))
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        avg_win = total_wins / len(winning_trades) if winning_trades else 0
        avg_loss = total_losses / len(losing_trades) if losing_trades else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else (total_wins if total_wins > 0 else 0)
        
        # Calculate drawdown
        equity_curve = []
        running_balance = 10.0  # Starting balance
        peak = running_balance
        max_drawdown = 0
        
        for trade in sorted(closed_trades, key=lambda x: x['time']):
            running_balance += trade['profit']
            equity_curve.append(running_balance)
            
            if running_balance > peak:
                peak = running_balance
            
            drawdown = (peak - running_balance) / peak if peak > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Calculate Sharpe Ratio (simplified)
        if len(equity_curve) > 1:
            returns = np.diff(equity_curve)
            sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            sharpe_ratio = sharpe_ratio * np.sqrt(252)  # Annualized
        else:
            sharpe_ratio = 0
        
        # Hourly performance (last 24 hours)
        hourly_data = defaultdict(lambda: {'profit': 0, 'trades': 0, 'wins': 0})
        now = datetime.now()
        for trade in closed_trades:
            trade_time = datetime.fromtimestamp(trade['time'])
            if (now - trade_time).total_seconds() <= 86400:  # Last 24 hours
                hour_key = trade_time.replace(minute=0, second=0, microsecond=0)
                hourly_data[hour_key]['profit'] += trade['profit']
                hourly_data[hour_key]['trades'] += 1
                if trade['profit'] > 0:
                    hourly_data[hour_key]['wins'] += 1
        
        hourly_list = []
        for hour in sorted(hourly_data.keys()):
            data = hourly_data[hour]
            hourly_list.append({
                'timestamp': hour.isoformat(),
                'profit': round(data['profit'], 2),
                'trades': data['trades'],
                'winRate': data['wins'] / data['trades'] if data['trades'] > 0 else 0
            })
        
        # Daily performance (last 30 days)
        daily_data = defaultdict(lambda: {'profit': 0, 'trades': 0, 'wins': 0})
        for trade in closed_trades:
            trade_time = datetime.fromtimestamp(trade['time'])
            day_key = trade_time.replace(hour=0, minute=0, second=0, microsecond=0)
            daily_data[day_key]['profit'] += trade['profit']
            daily_data[day_key]['trades'] += 1
            if trade['profit'] > 0:
                daily_data[day_key]['wins'] += 1
        
        daily_list = []
        for day in sorted(daily_data.keys()):
            data = daily_data[day]
            daily_list.append({
                'timestamp': day.isoformat(),
                'profit': round(data['profit'], 2),
                'trades': data['trades'],
                'winRate': data['wins'] / data['trades'] if data['trades'] > 0 else 0
            })
        
        # Symbol distribution
        symbol_trades = defaultdict(int)
        for trade in closed_trades:
            symbol_trades[trade['symbol']] += 1
        
        symbol_list = [{'symbol': k, 'trades': v} for k, v in symbol_trades.items()]
        symbol_list.sort(key=lambda x: x['trades'], reverse=True)
        
        # Recent trades
        recent_trades = sorted(closed_trades, key=lambda x: x['time'], reverse=True)[:20]
        recent_list = []
        for trade in recent_trades:
            recent_list.append({
                'time': datetime.fromtimestamp(trade['time']).isoformat(),
                'symbol': trade['symbol'],
                'type': trade['type'],
                'profit': round(trade['profit'], 2),
                'volume': trade['volume']
            })
        
        # Calculate expectancy
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        # Calculate recovery factor
        recovery_factor = abs(total_profit / (max_drawdown * 10)) if max_drawdown > 0 else 0
        
        # Calculate Calmar ratio
        calmar_ratio = (total_profit / 10) / max_drawdown if max_drawdown > 0 else 0
        
        return {
            "account": {
                "balance": account_info.balance,
                "equity": account_info.equity,
                "profit": account_info.profit,
                "margin": account_info.margin,
                "margin_free": account_info.margin_free
            },
            "overall": {
                "total_trades": total_trades,
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate": win_rate,
                "total_profit": round(total_profit, 2),
                "total_wins": round(total_wins, 2),
                "total_losses": round(total_losses, 2),
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "profit_factor": round(profit_factor, 2),
                "max_drawdown": round(max_drawdown * 100, 2),
                "sharpe_ratio": round(sharpe_ratio, 2),
                "expectancy": round(expectancy, 2),
                "recovery_factor": round(recovery_factor, 2),
                "calmar_ratio": round(calmar_ratio, 2),
                "best_trade": round(max([t['profit'] for t in closed_trades]), 2) if closed_trades else 0,
                "worst_trade": round(min([t['profit'] for t in closed_trades]), 2) if closed_trades else 0
            },
            "hourly": hourly_list,
            "daily": daily_list,
            "symbols": symbol_list,
            "trades": recent_list
        }
        
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    data = calculate_performance_metrics()
    if data:
        print(json.dumps(data))
    else:
        print(json.dumps({"error": "Failed to get performance data"}))
