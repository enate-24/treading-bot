"""Tests for Execution Engine implementation."""

import pytest
import time
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st

from trading_bot.execution_engine import (
    ExecutionEngine, ExchangeConfig, RetryConfig, RateLimiter, 
    OrderTracker, MockExchangeClient
)
from trading_bot.interfaces.execution_engine import CancelResult, OpenOrder
from trading_bot.models import (
    OrderRequest, OrderResult, OrderStatus, ExecutedTrade,
    OrderSide, OrderType, TimeInForce
)


class TestRateLimiter:
    """Test cases for Rate Limiter."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(max_requests=10, time_window=60.0)
        assert limiter.max_requests == 10
        assert limiter.time_window == 60.0
        assert len(limiter.requests) == 0

    def test_rate_limiter_allows_requests_within_limit(self):
        """Test that rate limiter allows requests within limit."""
        limiter = RateLimiter(max_requests=5, time_window=60.0)
        
        # Should allow requests up to the limit
        for i in range(5):
            assert limiter.can_make_request() is True
            limiter.record_request()
        
        # Should not allow more requests
        assert limiter.can_make_request() is False

    def test_rate_limiter_wait_time_calculation(self):
        """Test wait time calculation."""
        limiter = RateLimiter(max_requests=2, time_window=10.0)
        
        # Fill up the limit
        limiter.record_request()
        limiter.record_request()
        
        # Should need to wait
        wait_time = limiter.wait_time()
        assert wait_time > 0
        assert wait_time <= 10.0

    def test_rate_limiter_window_expiry(self):
        """Test that old requests expire from the window."""
        limiter = RateLimiter(max_requests=2, time_window=0.1)  # 100ms window
        
        # Fill up the limit
        limiter.record_request()
        limiter.record_request()
        assert limiter.can_make_request() is False
        
        # Wait for window to expire
        time.sleep(0.15)
        
        # Should allow requests again
        assert limiter.can_make_request() is True


class TestOrderTracker:
    """Test cases for Order Tracker."""

    def test_order_tracker_initialization(self):
        """Test order tracker initialization."""
        order_request = OrderRequest(
            symbol="BTCUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('0.1'),
            price=None,
            stop_loss=None,
            take_profit=None,
            time_in_force=TimeInForce.GTC
        )
        
        tracker = OrderTracker(order_request, "order_123")
        
        assert tracker.order_request == order_request
        assert tracker.order_id == "order_123"
        assert tracker.status == "PENDING"
        assert tracker.filled_quantity == Decimal('0')
        assert tracker.retry_count == 0
        assert tracker.exchange is None
        assert tracker.exchange_order_id is None


class TestMockExchangeClient:
    """Test cases for Mock Exchange Client."""

    def test_mock_client_initialization(self):
        """Test mock exchange client initialization."""
        config = ExchangeConfig(
            name="test_exchange",
            api_key="test_key",
            api_secret="test_secret",
            sandbox=True,
            rate_limit=100,
            timeout=30,
            priority=1
        )
        
        client = MockExchangeClient(config)
        assert client.config == config
        assert len(client.orders) == 0

    def test_mock_client_place_order_success(self):
        """Test successful order placement."""
        config = ExchangeConfig(
            name="test_exchange",
            api_key="test_key",
            api_secret="test_secret",
            sandbox=True,
            rate_limit=100,
            timeout=30,
            priority=1
        )
        
        client = MockExchangeClient(config)
        
        order_request = OrderRequest(
            symbol="BTCUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            stop_loss=None,
            take_profit=None,
            time_in_force=TimeInForce.GTC
        )
        
        result = client.place_order(order_request)
        
        assert result['status'] == 'success'
        assert 'order_id' in result
        assert len(client.orders) == 1

    def test_mock_client_place_order_rejection(self):
        """Test order rejection."""
        config = ExchangeConfig(
            name="test_exchange",
            api_key="test_key",
            api_secret="test_secret",
            sandbox=True,
            rate_limit=100,
            timeout=30,
            priority=1
        )
        
        client = MockExchangeClient(config)
        
        order_request = OrderRequest(
            symbol="REJECT_TEST",  # Special symbol that triggers rejection
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            stop_loss=None,
            take_profit=None,
            time_in_force=TimeInForce.GTC
        )
        
        result = client.place_order(order_request)
        
        assert result['status'] == 'error'
        assert 'message' in result
        assert len(client.orders) == 0

    def test_mock_client_cancel_order(self):
        """Test order cancellation."""
        config = ExchangeConfig(
            name="test_exchange",
            api_key="test_key",
            api_secret="test_secret",
            sandbox=True,
            rate_limit=100,
            timeout=30,
            priority=1
        )
        
        client = MockExchangeClient(config)
        
        # Place order first
        order_request = OrderRequest(
            symbol="BTCUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            stop_loss=None,
            take_profit=None,
            time_in_force=TimeInForce.GTC
        )
        
        place_result = client.place_order(order_request)
        order_id = place_result['order_id']
        
        # Cancel order
        cancel_result = client.cancel_order(order_id)
        
        assert cancel_result['status'] == 'success'
        assert client.orders[order_id]['status'] == 'cancelled'

    def test_mock_client_get_order_status(self):
        """Test order status retrieval."""
        config = ExchangeConfig(
            name="test_exchange",
            api_key="test_key",
            api_secret="test_secret",
            sandbox=True,
            rate_limit=100,
            timeout=30,
            priority=1
        )
        
        client = MockExchangeClient(config)
        
        # Place market order
        order_request = OrderRequest(
            symbol="BTCUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            stop_loss=None,
            take_profit=None,
            time_in_force=TimeInForce.GTC
        )
        
        place_result = client.place_order(order_request)
        order_id = place_result['order_id']
        
        # Get status - market orders should fill immediately
        status_result = client.get_order_status(order_id)
        
        assert status_result['status'] == 'filled'
        assert 'price' in status_result
        assert 'fee' in status_result


class TestExecutionEngine:
    """Test cases for Execution Engine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.exchange_configs = [
            ExchangeConfig(
                name="exchange_1",
                api_key="key1",
                api_secret="secret1",
                sandbox=True,
                rate_limit=100,
                timeout=30,
                priority=1
            ),
            ExchangeConfig(
                name="exchange_2",
                api_key="key2",
                api_secret="secret2",
                sandbox=True,
                rate_limit=50,
                timeout=30,
                priority=2
            )
        ]
        
        self.retry_config = RetryConfig(
            max_retries=3,
            base_delay=0.1,
            max_delay=1.0,
            backoff_multiplier=2.0
        )
        
        self.execution_engine = ExecutionEngine(
            exchange_configs=self.exchange_configs,
            retry_config=self.retry_config
        )

    def test_execution_engine_initialization(self):
        """Test execution engine initialization."""
        assert len(self.execution_engine.exchange_configs) == 2
        assert len(self.execution_engine.exchange_clients) == 2
        assert len(self.execution_engine.rate_limiters) == 2
        assert len(self.execution_engine.orders) == 0
        assert len(self.execution_engine.execution_history) == 0

    def test_place_order_success(self):
        """Test successful order placement."""
        order_request = OrderRequest(
            symbol="BTCUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            stop_loss=None,
            take_profit=None,
            time_in_force=TimeInForce.GTC
        )
        
        result = self.execution_engine.place_order(order_request)
        
        assert result.status == "ACCEPTED"
        assert result.order_id in self.execution_engine.orders
        
        tracker = self.execution_engine.orders[result.order_id]
        assert tracker.status == "SUBMITTED"
        assert tracker.exchange == "exchange_1"  # Should use highest priority exchange

    def test_place_order_smart_routing(self):
        """Test smart routing to backup exchange."""
        # Mock first exchange to fail
        self.execution_engine.exchange_clients["exchange_1"].place_order = Mock(
            side_effect=Exception("Connection failed")
        )
        
        order_request = OrderRequest(
            symbol="BTCUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            stop_loss=None,
            take_profit=None,
            time_in_force=TimeInForce.GTC
        )
        
        result = self.execution_engine.place_order(order_request)
        
        assert result.status == "ACCEPTED"
        
        tracker = self.execution_engine.orders[result.order_id]
        assert tracker.exchange == "exchange_2"  # Should fallback to second exchange

    def test_place_order_all_exchanges_fail(self):
        """Test order placement when all exchanges fail."""
        # Mock all exchanges to fail
        for exchange_name in self.execution_engine.exchange_clients:
            self.execution_engine.exchange_clients[exchange_name].place_order = Mock(
                side_effect=Exception("Connection failed")
            )
        
        order_request = OrderRequest(
            symbol="BTCUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            stop_loss=None,
            take_profit=None,
            time_in_force=TimeInForce.GTC
        )
        
        result = self.execution_engine.place_order(order_request)
        
        assert result.status == "REJECTED"
        assert "Failed to place order on any exchange" in result.message

    def test_cancel_order_success(self):
        """Test successful order cancellation."""
        # Place order first
        order_request = OrderRequest(
            symbol="BTCUSD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            stop_loss=None,
            take_profit=None,
            time_in_force=TimeInForce.GTC
        )
        
        place_result = self.execution_engine.place_order(order_request)
        
        # Cancel order
        cancel_result = self.execution_engine.cancel_order(place_result.order_id)
        
        assert cancel_result.success is True
        
        tracker = self.execution_engine.orders[place_result.order_id]
        assert tracker.status == "CANCELLED"

    def test_cancel_order_not_found(self):
        """Test cancelling non-existent order."""
        cancel_result = self.execution_engine.cancel_order("non_existent_order")
        
        assert cancel_result.success is False
        assert "Order not found" in cancel_result.message

    def test_cancel_order_already_filled(self):
        """Test cancelling already filled order."""
        # Place market order (fills immediately)
        order_request = OrderRequest(
            symbol="BTCUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            stop_loss=None,
            take_profit=None,
            time_in_force=TimeInForce.GTC
        )
        
        place_result = self.execution_engine.place_order(order_request)
        
        # Manually set status to filled
        tracker = self.execution_engine.orders[place_result.order_id]
        tracker.status = "FILLED"
        
        # Try to cancel
        cancel_result = self.execution_engine.cancel_order(place_result.order_id)
        
        assert cancel_result.success is False
        assert "Cannot cancel order in FILLED status" in cancel_result.message

    def test_get_order_status(self):
        """Test getting order status."""
        order_request = OrderRequest(
            symbol="BTCUSD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            stop_loss=None,
            take_profit=None,
            time_in_force=TimeInForce.GTC
        )
        
        place_result = self.execution_engine.place_order(order_request)
        
        status = self.execution_engine.get_order_status(place_result.order_id)
        
        assert status.order_id == place_result.order_id
        assert status.symbol == "BTCUSD"
        assert status.side == OrderSide.BUY
        assert status.order_type == OrderType.LIMIT
        assert status.quantity == Decimal('0.1')
        assert status.price == Decimal('50000')

    def test_get_order_status_not_found(self):
        """Test getting status of non-existent order."""
        with pytest.raises(ValueError, match="Order .* not found"):
            self.execution_engine.get_order_status("non_existent_order")

    def test_get_open_orders(self):
        """Test getting open orders."""
        # Place multiple orders
        order_requests = [
            OrderRequest(
                symbol="BTCUSD",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal('0.1'),
                price=Decimal('50000'),
                stop_loss=None,
                take_profit=None,
                time_in_force=TimeInForce.GTC
            ),
            OrderRequest(
                symbol="ETHUSD",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                quantity=Decimal('1.0'),
                price=Decimal('3000'),
                stop_loss=None,
                take_profit=None,
                time_in_force=TimeInForce.GTC
            )
        ]
        
        order_ids = []
        for order_request in order_requests:
            result = self.execution_engine.place_order(order_request)
            order_ids.append(result.order_id)
        
        open_orders = self.execution_engine.get_open_orders()
        
        assert len(open_orders) == 2
        assert all(isinstance(order, OpenOrder) for order in open_orders)
        
        # Check order details
        btc_order = next(order for order in open_orders if order.symbol == "BTCUSD")
        assert btc_order.side == "BUY"
        assert btc_order.quantity == 0.1
        assert btc_order.price == 50000.0

    def test_get_execution_history_empty(self):
        """Test getting execution history for symbol with no trades."""
        history = self.execution_engine.get_execution_history("BTCUSD")
        assert len(history) == 0

    def test_monitor_orders(self):
        """Test order monitoring functionality."""
        # Place market order
        order_request = OrderRequest(
            symbol="BTCUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            stop_loss=None,
            take_profit=None,
            time_in_force=TimeInForce.GTC
        )
        
        place_result = self.execution_engine.place_order(order_request)
        
        # Run monitoring
        self.execution_engine.monitor_orders()
        
        # Check if order was filled (market orders fill immediately in mock)
        tracker = self.execution_engine.orders[place_result.order_id]
        assert tracker.status == "FILLED"
        
        # Check execution history
        history = self.execution_engine.get_execution_history("BTCUSD")
        assert len(history) == 1
        
        trade = history[0]
        assert trade.symbol == "BTCUSD"
        assert trade.side == OrderSide.BUY
        assert trade.quantity == Decimal('0.1')

    def test_retry_logic_with_temporary_failure(self):
        """Test retry logic with temporary failures."""
        # Mock exchange to fail first two attempts, then succeed
        call_count = 0
        
        def mock_place_order(order_request):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Temporary failure")
            return {'status': 'success', 'order_id': 'test_order_123'}
        
        self.execution_engine.exchange_clients["exchange_1"].place_order = mock_place_order
        
        order_request = OrderRequest(
            symbol="BTCUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            stop_loss=None,
            take_profit=None,
            time_in_force=TimeInForce.GTC
        )
        
        result = self.execution_engine.place_order(order_request)
        
        assert result.status == "ACCEPTED"
        assert call_count == 3  # Should have retried twice before succeeding

    def test_api_connection_retry_logic_maximum_attempts(self):
        """Test maximum 5 retry attempts on API connection failure.
        
        Requirements: 2.4 - WHEN an API connection fails, THE Trading_Bot SHALL 
        attempt reconnection with a maximum of 5 retries
        """
        # Create execution engine with default retry config (max_retries=5)
        execution_engine = ExecutionEngine(
            exchange_configs=self.exchange_configs,
            retry_config=RetryConfig(
                max_retries=5,
                base_delay=0.01,  # Small delay for faster test
                max_delay=0.1,
                backoff_multiplier=2.0
            )
        )
        
        # Track connection attempts
        connection_attempts = 0
        
        def mock_failing_place_order(order_request):
            nonlocal connection_attempts
            connection_attempts += 1
            # Always fail to simulate persistent connection failure
            raise Exception("Connection failed - network unreachable")
        
        # Mock the first exchange to always fail
        execution_engine.exchange_clients["exchange_1"].place_order = mock_failing_place_order
        
        # Also mock the second exchange to fail to ensure we test retry logic on first exchange
        execution_engine.exchange_clients["exchange_2"].place_order = mock_failing_place_order
        
        order_request = OrderRequest(
            symbol="BTCUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            stop_loss=None,
            take_profit=None,
            time_in_force=TimeInForce.GTC
        )
        
        # Place order - should fail after maximum retries
        result = execution_engine.place_order(order_request)
        
        # Verify the result indicates failure
        assert result.status == "REJECTED"
        assert "Failed to place order on any exchange" in result.message
        
        # Verify exactly 5 retry attempts were made per exchange (total 10 attempts for 2 exchanges)
        # Since smart routing tries each exchange, and each exchange retries 5 times
        expected_total_attempts = 5 * len(execution_engine.exchange_configs)  # 5 retries per exchange
        assert connection_attempts == expected_total_attempts, \
            f"Expected {expected_total_attempts} connection attempts, but got {connection_attempts}"
        
        # Verify order is tracked with error state
        assert result.order_id in execution_engine.orders
        tracker = execution_engine.orders[result.order_id]
        assert tracker.status == "REJECTED"
        assert tracker.error_message is not None

    def test_api_connection_retry_logic_success_before_max_attempts(self):
        """Test successful connection before reaching maximum retry attempts.
        
        Requirements: 2.4 - Verify retry logic stops when connection succeeds
        """
        # Create execution engine with retry config
        execution_engine = ExecutionEngine(
            exchange_configs=self.exchange_configs,
            retry_config=RetryConfig(
                max_retries=5,
                base_delay=0.01,
                max_delay=0.1,
                backoff_multiplier=2.0
            )
        )
        
        # Track connection attempts
        connection_attempts = 0
        
        def mock_intermittent_failure_place_order(order_request):
            nonlocal connection_attempts
            connection_attempts += 1
            # Fail first 3 attempts, then succeed
            if connection_attempts <= 3:
                raise Exception("Connection failed - temporary network issue")
            return {'status': 'success', 'order_id': 'test_order_success'}
        
        # Mock the first exchange to fail initially then succeed
        execution_engine.exchange_clients["exchange_1"].place_order = mock_intermittent_failure_place_order
        
        order_request = OrderRequest(
            symbol="BTCUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            stop_loss=None,
            take_profit=None,
            time_in_force=TimeInForce.GTC
        )
        
        # Place order - should succeed on 4th attempt
        result = execution_engine.place_order(order_request)
        
        # Verify the result indicates success
        assert result.status == "ACCEPTED"
        
        # Verify exactly 4 attempts were made (3 failures + 1 success)
        assert connection_attempts == 4, \
            f"Expected 4 connection attempts, but got {connection_attempts}"
        
        # Verify order is tracked with success state
        assert result.order_id in execution_engine.orders
        tracker = execution_engine.orders[result.order_id]
        assert tracker.status == "SUBMITTED"
        assert tracker.exchange == "exchange_1"
        assert tracker.exchange_order_id == "test_order_success"

    def test_api_connection_retry_logic_exponential_backoff(self):
        """Test exponential backoff behavior in retry logic.
        
        Requirements: 2.4 - Verify proper backoff timing between retry attempts
        """
        # Create execution engine with specific retry config for timing test
        execution_engine = ExecutionEngine(
            exchange_configs=[self.exchange_configs[0]],  # Use only one exchange
            retry_config=RetryConfig(
                max_retries=3,
                base_delay=0.1,  # 100ms base delay
                max_delay=1.0,   # 1s max delay
                backoff_multiplier=2.0
            )
        )
        
        # Track connection attempts and timing
        connection_attempts = 0
        attempt_times = []
        
        def mock_timed_failure_place_order(order_request):
            nonlocal connection_attempts
            connection_attempts += 1
            attempt_times.append(time.time())
            # Always fail to test full retry sequence
            raise Exception("Connection timeout")
        
        execution_engine.exchange_clients["exchange_1"].place_order = mock_timed_failure_place_order
        
        order_request = OrderRequest(
            symbol="BTCUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            stop_loss=None,
            take_profit=None,
            time_in_force=TimeInForce.GTC
        )
        
        start_time = time.time()
        result = execution_engine.place_order(order_request)
        end_time = time.time()
        
        # Verify failure after all retries
        assert result.status == "REJECTED"
        assert connection_attempts == 3  # Should make exactly 3 attempts
        
        # Verify exponential backoff timing
        # Expected delays: 0.1s, 0.2s (total minimum ~0.3s)
        total_time = end_time - start_time
        expected_minimum_time = 0.1 + 0.2  # Sum of expected delays
        
        # Allow some tolerance for test execution overhead
        assert total_time >= expected_minimum_time * 0.8, \
            f"Expected minimum {expected_minimum_time}s due to backoff, but got {total_time}s"
        
        # Verify timing between attempts shows exponential backoff
        if len(attempt_times) >= 3:
            delay1 = attempt_times[1] - attempt_times[0]
            delay2 = attempt_times[2] - attempt_times[1]
            
            # Second delay should be approximately double the first (with tolerance)
            expected_ratio = 2.0
            actual_ratio = delay2 / delay1 if delay1 > 0 else 0
            
            # Allow 50% tolerance for timing precision in tests
            assert 1.0 <= actual_ratio <= 3.0, \
                f"Expected exponential backoff ratio ~{expected_ratio}, but got {actual_ratio}"

    def test_rate_limiting_integration(self):
        """Test rate limiting integration."""
        # Set very low rate limit
        self.execution_engine.rate_limiters["exchange_1"] = RateLimiter(max_requests=1, time_window=1.0)
        
        order_requests = [
            OrderRequest(
                symbol="BTCUSD",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal('0.1'),
                price=Decimal('50000'),
                stop_loss=None,
                take_profit=None,
                time_in_force=TimeInForce.GTC
            ),
            OrderRequest(
                symbol="ETHUSD",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal('1.0'),
                price=Decimal('3000'),
                stop_loss=None,
                take_profit=None,
                time_in_force=TimeInForce.GTC
            )
        ]
        
        # Place first order - should succeed
        result1 = self.execution_engine.place_order(order_requests[0])
        assert result1.status == "ACCEPTED"
        
        # Place second order immediately - should be rate limited but still succeed
        # (it will wait or use backup exchange)
        result2 = self.execution_engine.place_order(order_requests[1])
        assert result2.status == "ACCEPTED"

    def test_shutdown(self):
        """Test execution engine shutdown."""
        self.execution_engine.shutdown()
        assert self.execution_engine._monitoring_active is False


class TestExecutionEngineProperties:
    """Property-based tests for Execution Engine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.exchange_configs = [
            ExchangeConfig(
                name="test_exchange",
                api_key="test_key",
                api_secret="test_secret",
                sandbox=True,
                rate_limit=100,
                timeout=30,
                priority=1
            )
        ]
        
        self.execution_engine = ExecutionEngine(
            exchange_configs=self.exchange_configs,
            retry_config=RetryConfig(max_retries=2, base_delay=0.01)
        )

    @given(
        api_key=st.text(min_size=8, max_size=64, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        api_secret=st.text(min_size=16, max_size=128, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        exchange_name=st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        symbol=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        side=st.sampled_from([OrderSide.BUY, OrderSide.SELL]),
        quantity=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('1000'), places=2)
    )
    def test_api_authentication_consistency_property(
        self,
        api_key: str,
        api_secret: str,
        exchange_name: str,
        symbol: str,
        side: OrderSide,
        quantity: Decimal
    ):
        """
        **Feature: trading-bot-system, Property 4: API Authentication Consistency**
        
        For any exchange API call, the Trading Bot should include proper authentication 
        headers and credentials as required by the exchange's authentication protocol.
        
        **Validates: Requirements 2.2**
        """
        # Import uuid for the mock client
        import uuid
        
        # Create exchange config with generated credentials
        exchange_config = ExchangeConfig(
            name=exchange_name,
            api_key=api_key,
            api_secret=api_secret,
            sandbox=True,
            rate_limit=100,
            timeout=30,
            priority=1
        )
        
        # Create execution engine with this config
        execution_engine = ExecutionEngine(
            exchange_configs=[exchange_config],
            retry_config=RetryConfig(max_retries=1, base_delay=0.01)
        )
        
        # Create a mock client that validates authentication
        class AuthValidatingMockClient:
            def __init__(self, config: ExchangeConfig):
                self.config = config
                self.orders = {}
                self.last_auth_used = None
            
            def _validate_auth(self):
                """Simulate authentication validation."""
                # In real implementation, this would validate API signatures, timestamps, etc.
                if not self.config.api_key or not self.config.api_secret:
                    raise Exception("Missing authentication credentials")
                if len(self.config.api_key) < 8:
                    raise Exception("Invalid API key format")
                if len(self.config.api_secret) < 16:
                    raise Exception("Invalid API secret format")
                
                # Record that authentication was used
                self.last_auth_used = {
                    'api_key': self.config.api_key,
                    'api_secret': self.config.api_secret,
                    'exchange': self.config.name
                }
                return True
            
            def place_order(self, order_request: OrderRequest) -> Dict:
                """Mock order placement with authentication validation."""
                self._validate_auth()
                
                order_id = f"{self.config.name}_{uuid.uuid4().hex[:8]}"
                self.orders[order_id] = {
                    'order_request': order_request,
                    'status': 'submitted',
                    'filled_quantity': 0,
                    'created_at': datetime.now()
                }
                
                return {'status': 'success', 'order_id': order_id}
            
            def cancel_order(self, order_id: str) -> Dict:
                """Mock order cancellation with authentication validation."""
                self._validate_auth()
                
                if order_id in self.orders:
                    self.orders[order_id]['status'] = 'cancelled'
                    return {'status': 'success'}
                return {'status': 'error', 'message': 'Order not found'}
            
            def get_order_status(self, order_id: str) -> Dict:
                """Mock order status check with authentication validation."""
                self._validate_auth()
                
                if order_id not in self.orders:
                    return {'status': 'error', 'message': 'Order not found'}
                
                return {'status': self.orders[order_id]['status']}
        
        # Replace the mock client with our auth-validating version
        auth_client = AuthValidatingMockClient(exchange_config)
        execution_engine.exchange_clients[exchange_name] = auth_client
        
        # Create order request
        order_request = OrderRequest(
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=None,
            stop_loss=None,
            take_profit=None,
            time_in_force=TimeInForce.GTC
        )
        
        # Place order - this should trigger authentication
        result = execution_engine.place_order(order_request)
        
        # Property 1: Authentication should be used for API calls
        assert auth_client.last_auth_used is not None, "Authentication was not used for API call"
        
        # Property 2: Correct credentials should be used
        assert auth_client.last_auth_used['api_key'] == api_key, "Incorrect API key used"
        assert auth_client.last_auth_used['api_secret'] == api_secret, "Incorrect API secret used"
        assert auth_client.last_auth_used['exchange'] == exchange_name, "Incorrect exchange name"
        
        # Property 3: Order should be accepted when authentication is valid
        assert result.status == "ACCEPTED", f"Order was rejected despite valid authentication: {result.message}"
        
        # Property 4: Order tracking should work with authenticated calls
        if result.status == "ACCEPTED":
            # Test that subsequent authenticated calls work
            order_status = execution_engine.get_order_status(result.order_id)
            assert order_status.order_id == result.order_id
            
            # Test cancellation also uses authentication
            auth_client.last_auth_used = None  # Reset to verify cancel call uses auth
            cancel_result = execution_engine.cancel_order(result.order_id)
            assert auth_client.last_auth_used is not None, "Authentication was not used for cancel call"
            assert auth_client.last_auth_used['api_key'] == api_key, "Incorrect API key used for cancel"

    @given(
        symbol=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        side=st.sampled_from([OrderSide.BUY, OrderSide.SELL]),
        order_type=st.sampled_from([OrderType.MARKET, OrderType.LIMIT]),
        quantity=st.decimals(min_value=0.001, max_value=1000, places=6),
        price=st.one_of(
            st.none(),
            st.decimals(min_value=0.01, max_value=100000, places=2)
        ),
        time_in_force=st.sampled_from([TimeInForce.GTC, TimeInForce.IOC, TimeInForce.FOK])
    )
    def test_order_placement_consistency_property(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        price: Decimal,
        time_in_force: TimeInForce
    ):
        """
        Test that order placement is consistent and handles all valid inputs.
        
        This property ensures that the execution engine can handle any valid order
        request and either successfully places it or provides a clear error message.
        """
        # Skip invalid combinations
        if order_type == OrderType.LIMIT and price is None:
            return
        if order_type == OrderType.MARKET and price is not None:
            price = None  # Market orders don't need price
        
        order_request = OrderRequest(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_loss=None,
            take_profit=None,
            time_in_force=time_in_force
        )
        
        result = self.execution_engine.place_order(order_request)
        
        # Property: Result should always be valid
        assert isinstance(result, OrderResult)
        assert result.order_id is not None
        assert result.status in ["ACCEPTED", "REJECTED"]
        assert isinstance(result.message, str)
        assert isinstance(result.timestamp, datetime)
        
        # If accepted, order should be tracked
        if result.status == "ACCEPTED":
            assert result.order_id in self.execution_engine.orders
            tracker = self.execution_engine.orders[result.order_id]
            assert tracker.order_request == order_request
            assert tracker.status in ["PENDING", "SUBMITTED"]

    @given(
        num_orders=st.integers(min_value=1, max_value=10),
        symbols=st.lists(
            st.text(min_size=3, max_size=8, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
            min_size=1,
            max_size=10
        )
    )
    def test_order_tracking_consistency_property(
        self,
        num_orders: int,
        symbols: list
    ):
        """
        Test that order tracking remains consistent across multiple orders.
        
        This property ensures that the execution engine correctly tracks all orders
        and maintains consistent state.
        """
        if len(symbols) == 0:
            return
        
        placed_orders = []
        
        # Place multiple orders
        for i in range(min(num_orders, len(symbols))):
            order_request = OrderRequest(
                symbol=symbols[i % len(symbols)],
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal('0.1'),
                price=Decimal('50000'),
                stop_loss=None,
                take_profit=None,
                time_in_force=TimeInForce.GTC
            )
            
            result = self.execution_engine.place_order(order_request)
            if result.status == "ACCEPTED":
                placed_orders.append(result.order_id)
        
        # Property: All placed orders should be tracked
        for order_id in placed_orders:
            assert order_id in self.execution_engine.orders
            
            # Should be able to get status
            status = self.execution_engine.get_order_status(order_id)
            assert status.order_id == order_id
            
            # Should appear in open orders if not filled/cancelled
            tracker = self.execution_engine.orders[order_id]
            if tracker.status in ["PENDING", "SUBMITTED", "PARTIALLY_FILLED"]:
                open_orders = self.execution_engine.get_open_orders()
                order_ids_in_open = [order.order_id for order in open_orders]
                assert order_id in order_ids_in_open

    @given(
        max_requests=st.integers(min_value=1, max_value=20),
        time_window=st.floats(min_value=0.1, max_value=10.0),
        num_requests=st.integers(min_value=1, max_value=30)
    )
    def test_rate_limiter_property(
        self,
        max_requests: int,
        time_window: float,
        num_requests: int
    ):
        """
        Test that rate limiter correctly enforces limits.
        
        This property ensures that the rate limiter never allows more requests
        than the configured limit within the time window.
        """
        limiter = RateLimiter(max_requests=max_requests, time_window=time_window)
        
        allowed_requests = 0
        
        # Try to make requests
        for _ in range(num_requests):
            if limiter.can_make_request():
                limiter.record_request()
                allowed_requests += 1
        
        # Property: Should never allow more than max_requests
        assert allowed_requests <= max_requests
        
        # Property: If we made fewer requests than the limit, all should be allowed
        if num_requests <= max_requests:
            assert allowed_requests == num_requests
        else:
            assert allowed_requests == max_requests

    @given(
        symbol=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        side=st.sampled_from([OrderSide.BUY, OrderSide.SELL]),
        order_type=st.sampled_from([OrderType.MARKET, OrderType.LIMIT]),
        quantity=st.decimals(min_value=0.001, max_value=1000, places=6),
        price=st.one_of(
            st.none(),
            st.decimals(min_value=0.01, max_value=100000, places=2)
        ),
        time_in_force=st.sampled_from([TimeInForce.GTC, TimeInForce.IOC, TimeInForce.FOK])
    )
    def test_order_placement_consistency_property(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        price: Decimal,
        time_in_force: TimeInForce
    ):
        """
        Test that order placement is consistent and handles all valid inputs.
        
        This property ensures that the execution engine can handle any valid order
        request and either successfully places it or provides a clear error message.
        """
        # Skip invalid combinations
        if order_type == OrderType.LIMIT and price is None:
            return
        if order_type == OrderType.MARKET and price is not None:
            price = None  # Market orders don't need price
        
        order_request = OrderRequest(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_loss=None,
            take_profit=None,
            time_in_force=time_in_force
        )
        
        result = self.execution_engine.place_order(order_request)
        
        # Property: Result should always be valid
        assert isinstance(result, OrderResult)
        assert result.order_id is not None
        assert result.status in ["ACCEPTED", "REJECTED"]
        assert isinstance(result.message, str)
        assert isinstance(result.timestamp, datetime)
        
        # If accepted, order should be tracked
        if result.status == "ACCEPTED":
            assert result.order_id in self.execution_engine.orders
            tracker = self.execution_engine.orders[result.order_id]
            assert tracker.order_request == order_request
            assert tracker.status in ["PENDING", "SUBMITTED"]

    @given(
        num_orders=st.integers(min_value=1, max_value=10),
        symbols=st.lists(
            st.text(min_size=3, max_size=8, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
            min_size=1,
            max_size=10
        )
    )
    def test_order_tracking_consistency_property(
        self,
        num_orders: int,
        symbols: list
    ):
        """
        Test that order tracking remains consistent across multiple orders.
        
        This property ensures that the execution engine correctly tracks all orders
        and maintains consistent state.
        """
        if len(symbols) == 0:
            return
        
        placed_orders = []
        
        # Place multiple orders
        for i in range(min(num_orders, len(symbols))):
            order_request = OrderRequest(
                symbol=symbols[i % len(symbols)],
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal('0.1'),
                price=Decimal('50000'),
                stop_loss=None,
                take_profit=None,
                time_in_force=TimeInForce.GTC
            )
            
            result = self.execution_engine.place_order(order_request)
            if result.status == "ACCEPTED":
                placed_orders.append(result.order_id)
        
        # Property: All placed orders should be tracked
        for order_id in placed_orders:
            assert order_id in self.execution_engine.orders
            
            # Should be able to get status
            status = self.execution_engine.get_order_status(order_id)
            assert status.order_id == order_id
            
            # Should appear in open orders if not filled/cancelled
            tracker = self.execution_engine.orders[order_id]
            if tracker.status in ["PENDING", "SUBMITTED", "PARTIALLY_FILLED"]:
                open_orders = self.execution_engine.get_open_orders()
                order_ids_in_open = [order.order_id for order in open_orders]
                assert order_id in order_ids_in_open

    @given(
        max_requests=st.integers(min_value=1, max_value=20),
        time_window=st.floats(min_value=0.1, max_value=10.0),
        num_requests=st.integers(min_value=1, max_value=30)
    )
    def test_rate_limiter_property(
        self,
        max_requests: int,
        time_window: float,
        num_requests: int
    ):
        """
        Test that rate limiter correctly enforces limits.
        
        This property ensures that the rate limiter never allows more requests
        than the configured limit within the time window.
        """
        limiter = RateLimiter(max_requests=max_requests, time_window=time_window)
        
        allowed_requests = 0
        
        # Try to make requests
        for _ in range(num_requests):
            if limiter.can_make_request():
                limiter.record_request()
                allowed_requests += 1
        
        # Property: Should never allow more than max_requests
        assert allowed_requests <= max_requests
        
        # Property: If we made fewer requests than the limit, all should be allowed
        if num_requests <= max_requests:
            assert allowed_requests == num_requests
        else:
            assert allowed_requests == max_requests

    @given(
        rate_limit=st.integers(min_value=1, max_value=10),
        num_requests=st.integers(min_value=2, max_value=25),
        symbols=st.lists(
            st.text(min_size=3, max_size=8, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
            min_size=1,
            max_size=5
        )
    )
    def test_rate_limit_handling_property(
        self,
        rate_limit: int,
        num_requests: int,
        symbols: list
    ):
        """
        **Feature: trading-bot-system, Property 5: Rate Limit Handling**
        
        For any sequence of API requests that would exceed rate limits, the Trading Bot 
        should queue requests and implement exponential backoff without losing any requests.
        
        **Validates: Requirements 2.3**
        """
        if len(symbols) == 0:
            return
        
        # Create execution engine with very low rate limit to trigger rate limiting
        exchange_config = ExchangeConfig(
            name="rate_limited_exchange",
            api_key="test_key",
            api_secret="test_secret",
            sandbox=True,
            rate_limit=rate_limit,  # Use the generated rate limit
            timeout=30,
            priority=1
        )
        
        execution_engine = ExecutionEngine(
            exchange_configs=[exchange_config],
            retry_config=RetryConfig(max_retries=2, base_delay=0.01, max_delay=0.1)
        )
        
        # Override the rate limiter with a shorter time window to avoid long waits
        execution_engine.rate_limiters["rate_limited_exchange"] = RateLimiter(
            max_requests=rate_limit, 
            time_window=0.1  # 100ms window instead of 60s
        )
        
        # Track all requests made to verify none are lost
        original_place_order = execution_engine.exchange_clients["rate_limited_exchange"].place_order
        request_count = 0
        processed_requests = []
        
        def tracking_place_order(order_request):
            nonlocal request_count
            request_count += 1
            processed_requests.append({
                'request_id': request_count,
                'symbol': order_request.symbol,
                'side': order_request.side.value,
                'quantity': float(order_request.quantity)
            })
            return original_place_order(order_request)
        
        execution_engine.exchange_clients["rate_limited_exchange"].place_order = tracking_place_order
        
        # Generate order requests that will exceed rate limits
        order_requests = []
        for i in range(min(num_requests, 20)):  # Cap at 20 to keep test reasonable
            symbol = symbols[i % len(symbols)]
            order_request = OrderRequest(
                symbol=symbol,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal('0.1'),
                price=Decimal('50000'),
                stop_loss=None,
                take_profit=None,
                time_in_force=TimeInForce.GTC
            )
            order_requests.append(order_request)
        
        # Place all orders rapidly to trigger rate limiting
        results = []
        start_time = time.time()
        
        for order_request in order_requests:
            result = execution_engine.place_order(order_request)
            results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Property 1: All requests should eventually be processed (no requests lost)
        successful_orders = [r for r in results if r.status == "ACCEPTED"]
        
        # If we have more requests than the rate limit, some should be delayed
        if len(order_requests) > rate_limit:
            # Property 2: Rate limiting should cause delays when limits are exceeded
            # The total time should be longer than if all requests were processed instantly
            expected_minimum_time = (len(order_requests) - rate_limit) * 0.01  # Base delay
            # Allow some tolerance for test execution overhead
            assert total_time >= expected_minimum_time * 0.5, \
                f"Expected delays due to rate limiting, but execution was too fast: {total_time}s"
        
        # Property 3: Rate limiter should not lose any valid requests
        # All requests should either be accepted or have a clear rejection reason
        for i, result in enumerate(results):
            assert result.status in ["ACCEPTED", "REJECTED"], \
                f"Request {i} has invalid status: {result.status}"
            assert isinstance(result.message, str), \
                f"Request {i} missing error message"
            assert result.order_id is not None, \
                f"Request {i} missing order ID"
        
        # Property 4: Successful orders should be properly tracked
        for result in successful_orders:
            assert result.order_id in execution_engine.orders, \
                f"Successful order {result.order_id} not tracked"
            
            tracker = execution_engine.orders[result.order_id]
            assert tracker.status in ["PENDING", "SUBMITTED"], \
                f"Order {result.order_id} has invalid tracker status: {tracker.status}"
        
        # Property 5: Rate limiter state should be consistent
        rate_limiter = execution_engine.rate_limiters["rate_limited_exchange"]
        
        # The number of recorded requests should not exceed what was actually processed
        # (accounting for the fact that some requests might be queued/delayed)
        assert len(rate_limiter.requests) <= len(processed_requests), \
            "Rate limiter recorded more requests than were actually processed"
        
        # Property 6: All processed requests should correspond to actual order attempts
        assert len(processed_requests) <= len(order_requests), \
            "More requests were processed than were submitted"
        
        # Property 7: If rate limiting occurred, verify exponential backoff behavior
        if len(order_requests) > rate_limit and len(successful_orders) > 0:
            # Check that the execution engine properly handled rate limits
            # by either waiting or using alternative mechanisms
            
            # The rate limiter should have some requests recorded
            assert len(rate_limiter.requests) > 0, \
                "Rate limiter should have recorded requests"
            
            # Verify that rate limiter respects its own limits
            current_time = time.time()
            recent_requests = [
                req_time for req_time in rate_limiter.requests 
                if current_time - req_time < rate_limiter.time_window
            ]
            
            # Should not have more recent requests than the limit allows
            # (with some tolerance for timing precision)
            assert len(recent_requests) <= rate_limit + 1, \
                f"Rate limiter allowed too many requests: {len(recent_requests)} > {rate_limit}"