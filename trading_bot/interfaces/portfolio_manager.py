"""Portfolio Manager interface for position and risk management."""

from abc import ABC, abstractmethod
from typing import List
from decimal import Decimal
from ..models import TradingSignal, Position, ExecutedTrade, PortfolioMetrics


class IPortfolioManager(ABC):
    """Interface for portfolio management component."""

    @abstractmethod
    def calculate_position_size(self, signal: TradingSignal) -> Decimal:
        """Calculate optimal position size for a trading signal.
        
        Args:
            signal: Trading signal with strength and confidence
            
        Returns:
            Position size in base currency
        """
        pass

    @abstractmethod
    def get_current_positions(self) -> List[Position]:
        """Get all current open positions.
        
        Returns:
            List of current positions
        """
        pass

    @abstractmethod
    def get_available_capital(self) -> Decimal:
        """Get available capital for new positions.
        
        Returns:
            Available capital amount
        """
        pass

    @abstractmethod
    def update_position(self, trade: ExecutedTrade) -> None:
        """Update position based on executed trade.
        
        Args:
            trade: Executed trade information
        """
        pass

    @abstractmethod
    def get_portfolio_metrics(self) -> PortfolioMetrics:
        """Get current portfolio performance metrics.
        
        Returns:
            Portfolio metrics including PnL and positions
        """
        pass