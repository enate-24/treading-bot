"""Tests for Performance Monitor component."""

import pytest
import math
from decimal import Decimal
from datetime import datetime, timedelta
from trading_bot.performance_monitor import PerformanceMonitor
from trading_bot.models import ExecutedTrade, OrderSide


class TestPerformanceMonitor:
    """Test cases for Performance Monitor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.monitor = PerformanceMonitor(risk_free_rate=0.02)

    def test_initialization(self):
        """Test Performance Monitor initialization."""
        assert self.monitor._risk_free_rate == 0.02
        assert len(self.monitor._trades) == 0
        assert self.monitor._running_pnl == Decimal('0')
        assert self.monitor._winning_trades == 0
        assert self.monitor._losing_trades == 0

    def test_sharpe_ratio_calculation_empty_returns(self):
        """Test Sharpe ratio calculation with empty returns."""
        result = self.monitor.calculate_sharpe_ratio([])
        assert result == 0.0

    def test_sharpe_ratio_calculation_single_return(self):
        """Test Sharpe ratio calculation with single return."""
        result = self.monitor.calculate_sharpe_ratio([0.05])
        assert result == 0.0

    def test_sharpe_ratio_calculation_valid_returns(self):
        """Test Sharpe ratio calculation with valid returns."""
        # Daily returns of 1% with some variation
        returns = [0.01, 0.015, 0.005, 0.02, 0.008, 0.012, 0.018]
        result = self.monitor.calculate_sharpe_ratio(returns)
        
        # Should be positive since returns are above risk-free rate
        assert result > 0
        assert isinstance(result, float)

    def test_sharpe_ratio_calculation_zero_std(self):
        """Test Sharpe ratio calculation with zero standard deviation."""
        # All returns are the same
        returns = [0.01, 0.01, 0.01, 0.01]
        result = self.monitor.calculate_sharpe_ratio(returns)
        assert result == 0.0

    def test_sortino_ratio_calculation(self):
        """Test Sortino ratio calculation."""
        # Mix of positive and negative returns
        returns = [0.02, -0.01, 0.015, -0.005, 0.01, 0.008, -0.012]
        result = self.monitor.calculate_sortino_ratio(returns)
        
        assert isinstance(result, float)
        # Should be finite for mixed returns
        assert math.isfinite(result)

    def test_sortino_ratio_all_positive_returns(self):
        """Test Sortino ratio with all positive returns above risk-free rate."""
        returns = [0.01, 0.015, 0.02, 0.012]
        result = self.monitor.calculate_sortino_ratio(returns)
        
        # Should be very high (approaching infinity) since no downside
        assert result > 10  # Arbitrary high threshold

    def test_max_drawdown_calculation_empty(self):
        """Test max drawdown calculation with empty equity curve."""
        result = self.monitor.calculate_max_drawdown([])
        assert result == 0.0

    def test_max_drawdown_calculation_single_value(self):
        """Test max drawdown calculation with single value."""
        result = self.monitor.calculate_max_drawdown([1000.0])
        assert result == 0.0

    def test_max_drawdown_calculation_increasing_curve(self):
        """Test max drawdown calculation with always increasing equity."""
        equity_curve = [1000.0, 1100.0, 1200.0, 1300.0]
        result = self.monitor.calculate_max_drawdown(equity_curve)
        assert result == 0.0

    def test_max_drawdown_calculation_with_decline(self):
        """Test max drawdown calculation with equity decline."""
        equity_curve = [1000.0, 1200.0, 1100.0, 900.0, 1000.0]
        result = self.monitor.calculate_max_drawdown(equity_curve)
        
        # Max drawdown should be (1200 - 900) / 1200 = 0.25 (25%)
        expected_drawdown = (1200.0 - 900.0) / 1200.0
        assert abs(result - expected_drawdown) < 0.001

    def test_win_rate_calculation_no_trades(self):
        """Test win rate calculation with no trades."""
        result = self.monitor.calculate_win_rate()
        assert result == 0.0

    def test_win_rate_calculation_with_trades(self):
        """Test win rate calculation with mixed trades."""
        self.monitor._winning_trades = 7
        self.monitor._losing_trades = 3
        
        result = self.monitor.calculate_win_rate()
        assert result == 0.7  # 7/10 = 70%

    def test_profit_factor_calculation_no_losses(self):
        """Test profit factor calculation with no losses."""
        self.monitor._gross_profit = Decimal('1000')
        self.monitor._gross_loss = Decimal('0')
        
        result = self.monitor.calculate_profit_factor()
        assert result == float('inf')

    def test_profit_factor_calculation_normal(self):
        """Test profit factor calculation with normal values."""
        self.monitor._gross_profit = Decimal('1500')
        self.monitor._gross_loss = Decimal('-500')
        
        result = self.monitor.calculate_profit_factor()
        assert result == 3.0  # 1500 / 500 = 3.0

    def test_update_trade_metrics_winning_trade(self):
        """Test updating metrics with a winning trade."""
        trade = ExecutedTrade(
            trade_id="test_001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            fee=Decimal('5'),
            timestamp=datetime.now(),
            order_id="order_001"
        )
        
        initial_trades = len(self.monitor._trades)
        self.monitor.update_trade_metrics(trade)
        
        assert len(self.monitor._trades) == initial_trades + 1
        assert self.monitor._trades[-1] == trade
        assert len(self.monitor._equity_curve) > 0

    def test_update_trade_metrics_multiple_trades(self):
        """Test updating metrics with multiple trades."""
        trades = [
            ExecutedTrade(
                trade_id=f"test_{i:03d}",
                symbol="BTCUSDT",
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                quantity=Decimal('0.1'),
                price=Decimal('50000'),
                fee=Decimal('5'),
                timestamp=datetime.now() - timedelta(minutes=i),
                order_id=f"order_{i:03d}"
            )
            for i in range(5)
        ]
        
        for trade in trades:
            self.monitor.update_trade_metrics(trade)
        
        assert len(self.monitor._trades) == 5
        assert len(self.monitor._equity_curve) == 5
        assert self.monitor._winning_trades + self.monitor._losing_trades <= 5

    def test_generate_performance_report_no_trades(self):
        """Test generating performance report with no trades."""
        report = self.monitor.generate_performance_report("daily")
        
        assert report.period == "daily"
        assert report.total_trades == 0
        assert report.winning_trades == 0
        assert report.losing_trades == 0
        assert report.win_rate == 0.0
        assert report.total_pnl == Decimal('0')
        assert report.sharpe_ratio == 0.0
        assert report.max_drawdown == 0.0
        assert report.profit_factor == 0.0

    def test_generate_performance_report_with_trades(self):
        """Test generating performance report with trades."""
        # Add some test trades
        for i in range(3):
            trade = ExecutedTrade(
                trade_id=f"test_{i:03d}",
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=Decimal('0.1'),
                price=Decimal('50000'),
                fee=Decimal('5'),
                timestamp=datetime.now() - timedelta(hours=i),
                order_id=f"order_{i:03d}"
            )
            self.monitor.update_trade_metrics(trade)
        
        report = self.monitor.generate_performance_report("daily")
        
        assert report.period == "daily"
        assert report.total_trades == 3
        assert isinstance(report.win_rate, float)
        assert isinstance(report.sharpe_ratio, float)
        assert isinstance(report.max_drawdown, float)
        assert isinstance(report.profit_factor, float)

    def test_get_real_time_metrics(self):
        """Test getting real-time metrics."""
        metrics = self.monitor.get_real_time_metrics()
        
        # Check that all expected metrics are present
        expected_keys = [
            'total_trades', 'winning_trades', 'losing_trades', 'win_rate',
            'profit_factor', 'sharpe_ratio', 'sortino_ratio', 'max_drawdown',
            'current_drawdown', 'total_pnl', 'gross_profit', 'gross_loss',
            'avg_win_loss_ratio'
        ]
        
        for key in expected_keys:
            assert key in metrics
            assert isinstance(metrics[key], (int, float))

    def test_reset_metrics(self):
        """Test resetting all metrics."""
        # Add some trades first
        trade = ExecutedTrade(
            trade_id="test_001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            fee=Decimal('5'),
            timestamp=datetime.now(),
            order_id="order_001"
        )
        self.monitor.update_trade_metrics(trade)
        
        # Verify we have data
        assert len(self.monitor._trades) > 0
        assert self.monitor._running_pnl != Decimal('0')
        
        # Reset and verify everything is cleared
        self.monitor.reset_metrics()
        
        assert len(self.monitor._trades) == 0
        assert len(self.monitor._equity_curve) == 0
        assert len(self.monitor._returns) == 0
        assert self.monitor._running_pnl == Decimal('0')
        assert self.monitor._winning_trades == 0
        assert self.monitor._losing_trades == 0
        assert self.monitor._gross_profit == Decimal('0')
        assert self.monitor._gross_loss == Decimal('0')

    def test_get_trade_history(self):
        """Test getting trade history."""
        # Initially empty
        history = self.monitor.get_trade_history()
        assert len(history) == 0
        
        # Add a trade
        trade = ExecutedTrade(
            trade_id="test_001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            fee=Decimal('5'),
            timestamp=datetime.now(),
            order_id="order_001"
        )
        self.monitor.update_trade_metrics(trade)
        
        # Check history
        history = self.monitor.get_trade_history()
        assert len(history) == 1
        assert history[0] == trade

    def test_get_equity_curve(self):
        """Test getting equity curve."""
        # Initially empty
        curve = self.monitor.get_equity_curve()
        assert len(curve) == 0
        
        # Add trades and check curve grows
        for i in range(3):
            trade = ExecutedTrade(
                trade_id=f"test_{i:03d}",
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=Decimal('0.1'),
                price=Decimal('50000'),
                fee=Decimal('5'),
                timestamp=datetime.now() - timedelta(minutes=i),
                order_id=f"order_{i:03d}"
            )
            self.monitor.update_trade_metrics(trade)
        
        curve = self.monitor.get_equity_curve()
        assert len(curve) == 3
        assert all(isinstance(value, float) for value in curve)

    def test_filter_trades_by_period_all(self):
        """Test filtering trades by 'all' period."""
        # Add trades with different timestamps
        for i in range(3):
            trade = ExecutedTrade(
                trade_id=f"test_{i:03d}",
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=Decimal('0.1'),
                price=Decimal('50000'),
                fee=Decimal('5'),
                timestamp=datetime.now() - timedelta(days=i),
                order_id=f"order_{i:03d}"
            )
            self.monitor.update_trade_metrics(trade)
        
        filtered = self.monitor._filter_trades_by_period("all")
        assert len(filtered) == 3

    def test_filter_trades_by_period_daily(self):
        """Test filtering trades by daily period."""
        # Add trades: one recent, one old
        recent_trade = ExecutedTrade(
            trade_id="recent",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            fee=Decimal('5'),
            timestamp=datetime.now() - timedelta(hours=12),
            order_id="order_recent"
        )
        
        old_trade = ExecutedTrade(
            trade_id="old",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            fee=Decimal('5'),
            timestamp=datetime.now() - timedelta(days=2),
            order_id="order_old"
        )
        
        self.monitor.update_trade_metrics(recent_trade)
        self.monitor.update_trade_metrics(old_trade)
        
        filtered = self.monitor._filter_trades_by_period("daily")
        assert len(filtered) == 1
        assert filtered[0].trade_id == "recent"

    def test_average_win_loss_ratio_no_trades(self):
        """Test average win/loss ratio with no trades."""
        result = self.monitor.calculate_average_win_loss_ratio()
        assert result == 0.0

    def test_average_win_loss_ratio_no_losses(self):
        """Test average win/loss ratio with no losing trades."""
        self.monitor._winning_trades = 5
        self.monitor._losing_trades = 0
        self.monitor._gross_profit = Decimal('1000')
        
        result = self.monitor.calculate_average_win_loss_ratio()
        assert result == float('inf')

    def test_average_win_loss_ratio_normal(self):
        """Test average win/loss ratio with normal values."""
        self.monitor._winning_trades = 3
        self.monitor._losing_trades = 2
        self.monitor._gross_profit = Decimal('600')  # avg win = 200
        self.monitor._gross_loss = Decimal('-200')   # avg loss = 100
        
        result = self.monitor.calculate_average_win_loss_ratio()
        assert result == 2.0  # 200/100 = 2.0

    def test_generate_json_report(self):
        """Test generating performance report in JSON format."""
        # Add some test trades
        for i in range(2):
            trade = ExecutedTrade(
                trade_id=f"test_{i:03d}",
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=Decimal('0.1'),
                price=Decimal('50000'),
                fee=Decimal('5'),
                timestamp=datetime.now() - timedelta(hours=i),
                order_id=f"order_{i:03d}"
            )
            self.monitor.update_trade_metrics(trade)
        
        json_report = self.monitor.generate_json_report("daily")
        
        # Verify it's valid JSON
        import json
        report_data = json.loads(json_report)
        
        # Check required fields
        assert 'period' in report_data
        assert 'total_trades' in report_data
        assert 'win_rate' in report_data
        assert 'sharpe_ratio' in report_data
        assert 'timestamp' in report_data
        assert 'additional_metrics' in report_data
        
        assert report_data['period'] == 'daily'
        assert report_data['total_trades'] == 2

    def test_generate_csv_report(self):
        """Test generating performance report in CSV format."""
        # Add some test trades
        for i in range(2):
            trade = ExecutedTrade(
                trade_id=f"test_{i:03d}",
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=Decimal('0.1'),
                price=Decimal('50000'),
                fee=Decimal('5'),
                timestamp=datetime.now() - timedelta(hours=i),
                order_id=f"order_{i:03d}"
            )
            self.monitor.update_trade_metrics(trade)
        
        csv_report = self.monitor.generate_csv_report("daily")
        
        # Verify CSV format
        lines = csv_report.strip().split('\n')
        assert len(lines) == 2  # Header + 1 data row
        
        # Check header
        header = lines[0]
        assert 'Period' in header
        assert 'Total Trades' in header
        assert 'Win Rate' in header
        assert 'Sharpe Ratio' in header
        
        # Check data row
        data_row = lines[1]
        assert 'daily' in data_row
        assert '2' in data_row  # total trades

    def test_get_daily_performance_summary(self):
        """Test getting daily performance summary."""
        # Add trades on different days
        base_time = datetime.now()
        
        for i in range(3):
            trade = ExecutedTrade(
                trade_id=f"test_{i:03d}",
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=Decimal('0.1'),
                price=Decimal('50000'),
                fee=Decimal('5'),
                timestamp=base_time - timedelta(days=i),
                order_id=f"order_{i:03d}"
            )
            self.monitor.update_trade_metrics(trade)
        
        summary = self.monitor.get_daily_performance_summary()
        
        # Should have entries for each day
        assert len(summary) <= 3  # May be less if trades are on same day
        
        # Check structure of summary entries
        for date_key, daily_data in summary.items():
            assert 'trades' in daily_data
            assert 'pnl' in daily_data
            assert 'wins' in daily_data
            assert 'losses' in daily_data
            assert 'win_rate' in daily_data
            
            assert isinstance(daily_data['trades'], int)
            assert isinstance(daily_data['pnl'], float)
            assert isinstance(daily_data['win_rate'], float)