"""Risk Manager interface for risk control and validation."""

from abc import ABC, abstractmethod
from typing import Dict, Any
from decimal import Decimal
from ..models import OrderRequest, RiskMetrics


class RiskValidationResult:
    """Result of risk validation."""
    
    def __init__(self, approved: bool, reason: str = ""):
        self.approved = approved
        self.reason = reason


class IRiskManager(ABC):
    """Interface for risk management component."""

    @abstractmethod
    def validate_trade(self, trade_request: OrderRequest) -> RiskValidationResult:
        """Validate a trade request against risk parameters.
        
        Args:
            trade_request: Order request to validate
            
        Returns:
            Risk validation result with approval status
        """
        pass

    @abstractmethod
    def monitor_positions(self) -> None:
        """Monitor all positions for risk limit violations."""
        pass

    @abstractmethod
    def trigger_emergency_stop(self, reason: str) -> None:
        """Trigger emergency stop to halt all trading.
        
        Args:
            reason: Reason for emergency stop
        """
        pass

    @abstractmethod
    def update_stop_loss(self, position_id: str, new_stop: Decimal) -> None:
        """Update stop loss for a position.
        
        Args:
            position_id: Position identifier
            new_stop: New stop loss price
        """
        pass

    @abstractmethod
    def get_risk_metrics(self) -> RiskMetrics:
        """Get current risk metrics.
        
        Returns:
            Current risk metrics including drawdown and exposure
        """
        pass