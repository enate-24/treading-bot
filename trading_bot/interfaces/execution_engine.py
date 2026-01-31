"""Execution Engine interface for order management."""

from abc import ABC, abstractmethod
from typing import List
from ..models import OrderRequest, OrderResult, OrderStatus, ExecutedTrade


class CancelResult:
    """Result of order cancellation."""
    
    def __init__(self, success: bool, message: str = ""):
        self.success = success
        self.message = message


class OpenOrder:
    """Open order information."""
    
    def __init__(self, order_id: str, symbol: str, side: str, quantity: float, price: float):
        self.order_id = order_id
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.price = price


class IExecutionEngine(ABC):
    """Interface for order execution component."""

    @abstractmethod
    def place_order(self, order: OrderRequest) -> OrderResult:
        """Place a trading order.
        
        Args:
            order: Order request with all parameters
            
        Returns:
            Order result with status and order ID
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> CancelResult:
        """Cancel an existing order.
        
        Args:
            order_id: Order identifier to cancel
            
        Returns:
            Cancellation result
        """
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> OrderStatus:
        """Get status of an order.
        
        Args:
            order_id: Order identifier
            
        Returns:
            Current order status
        """
        pass

    @abstractmethod
    def get_execution_history(self, symbol: str) -> List[ExecutedTrade]:
        """Get execution history for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            List of executed trades
        """
        pass

    @abstractmethod
    def get_open_orders(self) -> List[OpenOrder]:
        """Get all open orders.
        
        Returns:
            List of open orders
        """
        pass