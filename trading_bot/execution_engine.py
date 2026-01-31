"""Execution Engine implementation for order management."""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
import uuid

from .interfaces.execution_engine import IExecutionEngine, CancelResult, OpenOrder
from .models import (
    OrderRequest, OrderResult, OrderStatus, ExecutedTrade, 
    OrderSide, OrderType, TimeInForce
)


@dataclass
class ExchangeConfig:
    """Configuration for exchange connection."""
    name: str
    api_key: str
    api_secret: str
    sandbox: bool
    rate_limit: int
    timeout: int
    priority: int  # For smart routing, lower number = higher priority


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0


class OrderTracker:
    """Tracks order state and execution."""
    
    def __init__(self, order_request: OrderRequest, order_id: str):
        self.order_request = order_request
        self.order_id = order_id
        self.status = "PENDING"
        self.filled_quantity = Decimal('0')
        self.average_price = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.retry_count = 0
        self.exchange = None
        self.exchange_order_id = None
        self.error_message = None


class RateLimiter:
    """Rate limiter for API calls."""
    
    def __init__(self, max_requests: int, time_window: float = 60.0):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def can_make_request(self) -> bool:
        """Check if a request can be made without exceeding rate limits."""
        now = time.time()
        # Remove old requests outside the time window
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.time_window]
        return len(self.requests) < self.max_requests
    
    def record_request(self):
        """Record a request timestamp."""
        self.requests.append(time.time())
    
    def wait_time(self) -> float:
        """Get time to wait before next request."""
        if self.can_make_request():
            return 0.0
        
        now = time.time()
        oldest_request = min(self.requests) if self.requests else now
        return self.time_window - (now - oldest_request)


class ExecutionEngine(IExecutionEngine):
    """Execution Engine for order management with smart routing and retry logic."""
    
    def __init__(self, exchange_configs: List[ExchangeConfig], retry_config: RetryConfig = None):
        self.logger = logging.getLogger(__name__)
        self.exchange_configs = sorted(exchange_configs, key=lambda x: x.priority)
        self.retry_config = retry_config or RetryConfig()
        
        # Order tracking
        self.orders: Dict[str, OrderTracker] = {}
        self.execution_history: Dict[str, List[ExecutedTrade]] = {}
        
        # Rate limiting per exchange
        self.rate_limiters: Dict[str, RateLimiter] = {}
        for config in exchange_configs:
            self.rate_limiters[config.name] = RateLimiter(config.rate_limit)
        
        # Mock exchange connections (in real implementation, these would be actual exchange clients)
        self.exchange_clients: Dict[str, Any] = {}
        self._initialize_exchange_clients()
        
        # Background task for order monitoring
        self._monitoring_active = True
        self._start_order_monitoring()
    
    def _initialize_exchange_clients(self):
        """Initialize exchange client connections."""
        for config in self.exchange_configs:
            # In real implementation, this would create actual exchange client instances
            # For now, we'll use mock clients
            self.exchange_clients[config.name] = MockExchangeClient(config)
            self.logger.info(f"Initialized connection to {config.name}")
    
    def place_order(self, order: OrderRequest) -> OrderResult:
        """Place a trading order with smart routing and retry logic."""
        order_id = str(uuid.uuid4())
        tracker = OrderTracker(order, order_id)
        self.orders[order_id] = tracker
        
        self.logger.info(f"Placing order {order_id}: {order.side.value} {order.quantity} {order.symbol}")
        
        # Smart routing: try exchanges in priority order
        for exchange_config in self.exchange_configs:
            try:
                result = self._place_order_on_exchange(tracker, exchange_config)
                if result.status == "ACCEPTED":
                    tracker.exchange = exchange_config.name
                    tracker.status = "SUBMITTED"
                    tracker.updated_at = datetime.now()
                    self.logger.info(f"Order {order_id} placed on {exchange_config.name}")
                    return result
            except Exception as e:
                self.logger.warning(f"Failed to place order on {exchange_config.name}: {e}")
                continue
        
        # If all exchanges failed
        tracker.status = "REJECTED"
        tracker.error_message = "All exchanges failed"
        return OrderResult(
            order_id=order_id,
            status="REJECTED",
            message="Failed to place order on any exchange",
            timestamp=datetime.now()
        )
    
    def _place_order_on_exchange(self, tracker: OrderTracker, exchange_config: ExchangeConfig) -> OrderResult:
        """Place order on specific exchange with rate limiting and retry."""
        exchange_name = exchange_config.name
        rate_limiter = self.rate_limiters[exchange_name]
        
        # Check rate limits
        if not rate_limiter.can_make_request():
            wait_time = rate_limiter.wait_time()
            if wait_time > 0:
                self.logger.info(f"Rate limit hit for {exchange_name}, waiting {wait_time:.2f}s")
                time.sleep(wait_time)
        
        # Retry logic with exponential backoff
        for attempt in range(self.retry_config.max_retries):
            try:
                rate_limiter.record_request()
                client = self.exchange_clients[exchange_name]
                
                # Place order on exchange
                exchange_result = client.place_order(tracker.order_request)
                
                if exchange_result['status'] == 'success':
                    tracker.exchange_order_id = exchange_result['order_id']
                    return OrderResult(
                        order_id=tracker.order_id,
                        status="ACCEPTED",
                        message=f"Order placed on {exchange_name}",
                        timestamp=datetime.now()
                    )
                else:
                    raise Exception(f"Exchange rejected order: {exchange_result.get('message', 'Unknown error')}")
                    
            except Exception as e:
                tracker.retry_count += 1
                self.logger.warning(f"Order placement attempt {attempt + 1} failed on {exchange_name}: {e}")
                
                if attempt < self.retry_config.max_retries - 1:
                    delay = min(
                        self.retry_config.base_delay * (self.retry_config.backoff_multiplier ** attempt),
                        self.retry_config.max_delay
                    )
                    time.sleep(delay)
                else:
                    tracker.error_message = str(e)
                    raise e
    
    def cancel_order(self, order_id: str) -> CancelResult:
        """Cancel an existing order."""
        if order_id not in self.orders:
            return CancelResult(False, "Order not found")
        
        tracker = self.orders[order_id]
        
        if tracker.status in ["FILLED", "CANCELLED", "REJECTED"]:
            return CancelResult(False, f"Cannot cancel order in {tracker.status} status")
        
        try:
            if tracker.exchange and tracker.exchange_order_id:
                client = self.exchange_clients[tracker.exchange]
                result = client.cancel_order(tracker.exchange_order_id)
                
                if result['status'] == 'success':
                    tracker.status = "CANCELLED"
                    tracker.updated_at = datetime.now()
                    self.logger.info(f"Order {order_id} cancelled successfully")
                    return CancelResult(True, "Order cancelled successfully")
                else:
                    return CancelResult(False, f"Exchange cancellation failed: {result.get('message', 'Unknown error')}")
            else:
                # Order not yet submitted to exchange
                tracker.status = "CANCELLED"
                tracker.updated_at = datetime.now()
                return CancelResult(True, "Order cancelled before submission")
                
        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            return CancelResult(False, f"Cancellation error: {str(e)}")
    
    def get_order_status(self, order_id: str) -> OrderStatus:
        """Get status of an order."""
        if order_id not in self.orders:
            raise ValueError(f"Order {order_id} not found")
        
        tracker = self.orders[order_id]
        
        return OrderStatus(
            order_id=order_id,
            symbol=tracker.order_request.symbol,
            side=tracker.order_request.side,
            order_type=tracker.order_request.order_type,
            quantity=tracker.order_request.quantity,
            filled_quantity=tracker.filled_quantity,
            price=tracker.order_request.price,
            status=tracker.status,
            timestamp=tracker.updated_at
        )
    
    def get_execution_history(self, symbol: str) -> List[ExecutedTrade]:
        """Get execution history for a symbol."""
        return self.execution_history.get(symbol, [])
    
    def get_open_orders(self) -> List[OpenOrder]:
        """Get all open orders."""
        open_orders = []
        
        for order_id, tracker in self.orders.items():
            if tracker.status in ["PENDING", "SUBMITTED", "PARTIALLY_FILLED"]:
                open_orders.append(OpenOrder(
                    order_id=order_id,
                    symbol=tracker.order_request.symbol,
                    side=tracker.order_request.side.value,
                    quantity=float(tracker.order_request.quantity),
                    price=float(tracker.order_request.price) if tracker.order_request.price else 0.0
                ))
        
        return open_orders
    
    def _start_order_monitoring(self):
        """Start background order monitoring."""
        # In a real implementation, this would run in a separate thread or async task
        # For now, we'll implement a simple monitoring method that can be called periodically
        pass
    
    def monitor_orders(self):
        """Monitor order status and update tracking."""
        for order_id, tracker in self.orders.items():
            if tracker.status in ["SUBMITTED", "PARTIALLY_FILLED"] and tracker.exchange:
                try:
                    client = self.exchange_clients[tracker.exchange]
                    status_result = client.get_order_status(tracker.exchange_order_id)
                    
                    if status_result['status'] == 'filled':
                        self._handle_order_fill(tracker, status_result)
                    elif status_result['status'] == 'partially_filled':
                        self._handle_partial_fill(tracker, status_result)
                    elif status_result['status'] == 'cancelled':
                        tracker.status = "CANCELLED"
                        tracker.updated_at = datetime.now()
                        
                except Exception as e:
                    self.logger.error(f"Error monitoring order {order_id}: {e}")
    
    def _handle_order_fill(self, tracker: OrderTracker, fill_data: Dict):
        """Handle complete order fill."""
        tracker.status = "FILLED"
        tracker.filled_quantity = tracker.order_request.quantity
        tracker.average_price = Decimal(str(fill_data['price']))
        tracker.updated_at = datetime.now()
        
        # Create executed trade record
        trade = ExecutedTrade(
            trade_id=str(uuid.uuid4()),
            symbol=tracker.order_request.symbol,
            side=tracker.order_request.side,
            quantity=tracker.order_request.quantity,
            price=tracker.average_price,
            fee=Decimal(str(fill_data.get('fee', 0))),
            timestamp=datetime.now(),
            order_id=tracker.order_id
        )
        
        # Add to execution history
        symbol = tracker.order_request.symbol
        if symbol not in self.execution_history:
            self.execution_history[symbol] = []
        self.execution_history[symbol].append(trade)
        
        self.logger.info(f"Order {tracker.order_id} filled: {trade.quantity} @ {trade.price}")
    
    def _handle_partial_fill(self, tracker: OrderTracker, fill_data: Dict):
        """Handle partial order fill."""
        tracker.status = "PARTIALLY_FILLED"
        tracker.filled_quantity = Decimal(str(fill_data['filled_quantity']))
        tracker.updated_at = datetime.now()
        
        self.logger.info(f"Order {tracker.order_id} partially filled: {tracker.filled_quantity}/{tracker.order_request.quantity}")
    
    def shutdown(self):
        """Shutdown the execution engine."""
        self._monitoring_active = False
        self.logger.info("Execution engine shutdown")


class MockExchangeClient:
    """Mock exchange client for testing purposes."""
    
    def __init__(self, config: ExchangeConfig):
        self.config = config
        self.orders = {}
    
    def place_order(self, order_request: OrderRequest) -> Dict:
        """Mock order placement."""
        # Simulate some orders being rejected
        if order_request.symbol == "REJECT_TEST":
            return {'status': 'error', 'message': 'Symbol not supported'}
        
        order_id = f"{self.config.name}_{uuid.uuid4().hex[:8]}"
        self.orders[order_id] = {
            'order_request': order_request,
            'status': 'submitted',
            'filled_quantity': 0,
            'created_at': datetime.now()
        }
        
        return {'status': 'success', 'order_id': order_id}
    
    def cancel_order(self, order_id: str) -> Dict:
        """Mock order cancellation."""
        if order_id in self.orders:
            self.orders[order_id]['status'] = 'cancelled'
            return {'status': 'success'}
        return {'status': 'error', 'message': 'Order not found'}
    
    def get_order_status(self, order_id: str) -> Dict:
        """Mock order status check."""
        if order_id not in self.orders:
            return {'status': 'error', 'message': 'Order not found'}
        
        order = self.orders[order_id]
        
        # Simulate order progression
        if order['status'] == 'submitted':
            # Simulate some orders filling quickly
            if order['order_request'].order_type == OrderType.MARKET:
                order['status'] = 'filled'
                return {
                    'status': 'filled',
                    'price': float(order['order_request'].price or 100.0),
                    'fee': 0.1
                }
        
        return {'status': order['status']}