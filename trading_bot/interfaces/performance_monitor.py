"""Performance Monitor interface for metrics calculation."""

from abc import ABC, abstractmethod
from typing import List, Dict
from ..models import ExecutedTrade, PerformanceReport


class IPerformanceMonitor(ABC):
    """Interface for performance monitoring component."""

    @abstractmethod
    def calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """Calculate Sharpe ratio from returns.
        
        Args:
            returns: List of trading returns
            
        Returns:
            Sharpe ratio value
        """
        pass

    @abstractmethod
    def calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """Calculate maximum drawdown from equity curve.
        
        Args:
            equity_curve: List of portfolio values over time
            
        Returns:
            Maximum drawdown percentage
        """
        pass

    @abstractmethod
    def generate_performance_report(self, period: str) -> PerformanceReport:
        """Generate performance report for specified period.
        
        Args:
            period: Time period for report (e.g., 'daily', 'weekly', 'monthly')
            
        Returns:
            Performance report with key metrics
        """
        pass

    @abstractmethod
    def update_trade_metrics(self, trade: ExecutedTrade) -> None:
        """Update performance metrics with new trade.
        
        Args:
            trade: Executed trade to include in metrics
        """
        pass

    @abstractmethod
    def get_real_time_metrics(self) -> Dict[str, float]:
        """Get real-time performance metrics.
        
        Returns:
            Dictionary of current performance metrics
        """
        pass