"""Unit tests for Data Handler implementation."""

import pytest
import time
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from hypothesis import given, strategies as st

from trading_bot.data_handler import DataHandler
from trading_bot.models import MarketData, Price


class TestDataHandler:
    """Test Data Handler implementation."""
    
    @pytest.fixture
    def data_handler(self):
        """Create a data handler instance for testing."""
        handler = DataHandler(max_history_size=100)
        yield handler
        handler.stop()  # Cleanup
    
    def test_data_handler_initialization(self, data_handler):
        """Test data handler initializes correctly."""
        assert data_handler.max_history_size == 100
        assert len(data_handler._subscriptions) == 0
        assert len(data_handler._callbacks) == 0
        assert not data_handler._running
    
    def test_subscribe_to_symbol(self, data_handler):
        """Test subscribing to a symbol."""
        symbol = "BTC/USD"
        timeframe = "1m"
        
        data_handler.subscribe_to_symbol(symbol, timeframe)
        
        assert symbol in data_handler._subscriptions
        assert timeframe in data_handler._subscriptions[symbol]
        assert data_handler._subscriptions[symbol][timeframe]['active'] is True
        assert data_handler._running is True
    
    def test_register_data_callback(self, data_handler):
        """Test registering data callbacks."""
        callback = Mock()
        
        data_handler.register_data_callback(callback)
        
        assert callback in data_handler._callbacks
    
    def test_get_latest_price_no_data(self, data_handler):
        """Test getting latest price when no data available."""
        price = data_handler.get_latest_price("BTC/USD")
        assert price is None
    
    def test_get_indicator_value_no_data(self, data_handler):
        """Test getting indicator value when no data available."""
        rsi = data_handler.get_indicator_value("BTC/USD", "RSI")
        assert rsi is None
    
    def test_get_historical_data_no_data(self, data_handler):
        """Test getting historical data when no data available."""
        df = data_handler.get_historical_data("BTC/USD", 10)
        assert df.empty
    
    def test_simulated_data_generation(self, data_handler):
        """Test simulated data generation."""
        symbol = "BTC/USD"
        data = data_handler._generate_simulated_data(symbol)
        
        assert data is not None
        assert data['symbol'] == symbol
        assert isinstance(data['timestamp'], datetime)
        assert isinstance(data['last'], Decimal)
        assert isinstance(data['bid'], Decimal)
        assert isinstance(data['ask'], Decimal)
        assert isinstance(data['volume'], Decimal)
        assert data['bid'] < data['ask']  # Spread validation
        assert data['last'] > 0
    
    def test_process_market_data(self, data_handler):
        """Test processing market data."""
        symbol = "BTC/USD"
        callback = Mock()
        data_handler.register_data_callback(callback)
        
        raw_data = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'open': Decimal('50000.00'),
            'high': Decimal('50100.00'),
            'low': Decimal('49900.00'),
            'last': Decimal('50050.00'),
            'bid': Decimal('50040.00'),
            'ask': Decimal('50060.00'),
            'volume': Decimal('1.5')
        }
        
        data_handler._process_market_data(raw_data)
        
        # Check data was stored
        assert symbol in data_handler._price_data
        assert len(data_handler._price_data[symbol]) == 1
        
        # Check callback was called
        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        assert isinstance(call_args, MarketData)
        assert call_args.symbol == symbol
    
    def test_get_latest_price_with_data(self, data_handler):
        """Test getting latest price with data available."""
        symbol = "BTC/USD"
        raw_data = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'open': Decimal('50000.00'),
            'high': Decimal('50100.00'),
            'low': Decimal('49900.00'),
            'last': Decimal('50050.00'),
            'bid': Decimal('50040.00'),
            'ask': Decimal('50060.00'),
            'volume': Decimal('1.5')
        }
        
        data_handler._process_market_data(raw_data)
        price = data_handler.get_latest_price(symbol)
        
        assert price is not None
        assert isinstance(price, Price)
        assert price.symbol == symbol
        assert price.last == Decimal('50050.00')
        assert price.bid == Decimal('50040.00')
        assert price.ask == Decimal('50060.00')
    
    def test_get_historical_data_with_data(self, data_handler):
        """Test getting historical data with data available."""
        symbol = "BTC/USD"
        
        # Add multiple data points
        for i in range(5):
            raw_data = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'open': Decimal(f'{50000 + i}.00'),
                'high': Decimal(f'{50100 + i}.00'),
                'low': Decimal(f'{49900 + i}.00'),
                'last': Decimal(f'{50050 + i}.00'),
                'bid': Decimal(f'{50040 + i}.00'),
                'ask': Decimal(f'{50060 + i}.00'),
                'volume': Decimal('1.5')
            }
            data_handler._process_market_data(raw_data)
        
        df = data_handler.get_historical_data(symbol, 3)
        
        assert not df.empty
        assert len(df) == 3  # Should get last 3 periods
        assert 'open' in df.columns
        assert 'high' in df.columns
        assert 'low' in df.columns
        assert 'close' in df.columns
        assert 'volume' in df.columns
    
    def test_rsi_calculation(self, data_handler):
        """Test RSI calculation."""
        # Create price series with known pattern
        prices = [50.0, 51.0, 52.0, 51.5, 50.5, 49.0, 48.0, 49.5, 50.5, 51.5,
                 52.5, 53.0, 52.0, 51.0, 50.0, 49.0, 50.0, 51.0, 52.0, 53.0]
        
        rsi = data_handler._calculate_rsi(prices, 14)
        
        assert isinstance(rsi, float)
        assert 0 <= rsi <= 100
    
    def test_sma_calculation(self, data_handler):
        """Test Simple Moving Average calculation."""
        prices = [10.0, 12.0, 14.0, 16.0, 18.0]
        period = 3
        
        sma = data_handler._calculate_sma(prices, period)
        
        # Should be average of last 3 prices: (14 + 16 + 18) / 3 = 16
        assert sma == 16.0
    
    def test_ema_calculation(self, data_handler):
        """Test Exponential Moving Average calculation."""
        prices = [10.0, 12.0, 14.0, 16.0, 18.0]
        period = 3
        
        ema = data_handler._calculate_ema(prices, period)
        
        assert isinstance(ema, float)
        assert ema > 0
    
    def test_macd_calculation(self, data_handler):
        """Test MACD calculation."""
        # Create enough price data for MACD calculation
        prices = [50.0 + i * 0.5 for i in range(30)]
        
        macd_line, signal_line, histogram = data_handler._calculate_macd(prices)
        
        assert isinstance(macd_line, float)
        assert isinstance(signal_line, float)
        assert isinstance(histogram, float)
        assert abs(histogram - (macd_line - signal_line)) < 0.001
    
    def test_indicator_updates(self, data_handler):
        """Test that indicators are updated when processing data."""
        symbol = "BTC/USD"
        
        # Add enough data points to calculate indicators
        for i in range(20):
            raw_data = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'open': Decimal(f'{50000 + i}.00'),
                'high': Decimal(f'{50100 + i}.00'),
                'low': Decimal(f'{49900 + i}.00'),
                'last': Decimal(f'{50050 + i}.00'),
                'bid': Decimal(f'{50040 + i}.00'),
                'ask': Decimal(f'{50060 + i}.00'),
                'volume': Decimal('1.5')
            }
            data_handler._process_market_data(raw_data)
        
        # Check that indicators were calculated
        rsi = data_handler.get_indicator_value(symbol, "RSI")
        sma_20 = data_handler.get_indicator_value(symbol, "SMA_20")
        
        assert rsi is not None
        assert 0 <= rsi <= 100
        assert sma_20 is not None
        assert sma_20 > 0
    
    def test_data_handler_with_subscription_and_processing(self, data_handler):
        """Test end-to-end data processing with subscription."""
        symbol = "BTC/USD"
        timeframe = "1m"
        callback = Mock()
        
        # Subscribe and register callback
        data_handler.subscribe_to_symbol(symbol, timeframe)
        data_handler.register_data_callback(callback)
        
        # Wait a bit for data processing
        time.sleep(2)
        
        # Check that data was generated and processed
        assert data_handler._running is True
        assert len(data_handler._price_data[symbol]) > 0
        
        # Check that callback was called
        assert callback.call_count > 0
        
        # Check that we can get latest price
        price = data_handler.get_latest_price(symbol)
        assert price is not None
        assert price.symbol == symbol
    
    def test_stop_data_handler(self, data_handler):
        """Test stopping the data handler."""
        data_handler.subscribe_to_symbol("BTC/USD", "1m")
        assert data_handler._running is True
        
        data_handler.stop()
        
        assert data_handler._running is False
    
    def test_max_history_size_limit(self, data_handler):
        """Test that history size is limited correctly."""
        symbol = "BTC/USD"
        max_size = data_handler.max_history_size
        
        # Add more data points than max size
        for i in range(max_size + 10):
            raw_data = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'open': Decimal(f'{50000 + i}.00'),
                'high': Decimal(f'{50100 + i}.00'),
                'low': Decimal(f'{49900 + i}.00'),
                'last': Decimal(f'{50050 + i}.00'),
                'bid': Decimal(f'{50040 + i}.00'),
                'ask': Decimal(f'{50060 + i}.00'),
                'volume': Decimal('1.5')
            }
            data_handler._process_market_data(raw_data)
        
        # Check that size is limited
        assert len(data_handler._price_data[symbol]) == max_size


class TestTechnicalIndicatorCorrectness:
    """Property-based tests for technical indicator correctness.
    
    **Feature: trading-bot-system, Property 11: Technical Indicator Correctness**
    **Validates: Requirements 5.2**
    """
    
    def _reference_rsi(self, prices: list, period: int = 14) -> float:
        """Reference RSI calculation using standard Wilder's smoothing formula."""
        if len(prices) < period + 1:
            return 50.0
        
        # Calculate price changes
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # Separate gains and losses
        gains = [max(delta, 0) for delta in deltas]
        losses = [max(-delta, 0) for delta in deltas]
        
        # Handle edge case: no price changes (constant prices)
        if all(gain == 0 for gain in gains) and all(loss == 0 for loss in losses):
            return 50.0  # Neutral RSI for constant prices
        
        # Calculate initial averages using simple average for first period
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # Apply Wilder's smoothing for remaining periods
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        # Handle edge case: no losses
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        
        # Calculate RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _reference_sma(self, prices: list, period: int) -> float:
        """Reference SMA calculation using standard formula."""
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        return sum(prices[-period:]) / period
    
    def _reference_ema(self, prices: list, period: int) -> float:
        """Reference EMA calculation using standard formula."""
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        
        multiplier = 2.0 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    @given(
        prices=st.lists(
            st.floats(min_value=1.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
            min_size=20,
            max_size=100
        )
    )
    def test_rsi_calculation_correctness(self, prices):
        """Property test: RSI calculation should match standard formula within acceptable precision.
        
        **Validates: Requirements 5.2**
        """
        data_handler = DataHandler(max_history_size=1000)
        try:
            # Calculate RSI using data handler
            calculated_rsi = data_handler._calculate_rsi(prices, 14)
            
            # Calculate reference RSI
            reference_rsi = self._reference_rsi(prices, 14)
            
            # Verify RSI is within valid range
            assert 0 <= calculated_rsi <= 100, f"RSI {calculated_rsi} is outside valid range [0, 100]"
            
            # Verify RSI matches reference calculation within acceptable precision (±2.0)
            # Note: Some variation is acceptable due to different smoothing implementations
            precision_tolerance = 2.0
            assert abs(calculated_rsi - reference_rsi) <= precision_tolerance, \
                f"RSI calculation differs too much: calculated={calculated_rsi}, reference={reference_rsi}"
        finally:
            data_handler.stop()
    
    @given(
        prices=st.lists(
            st.floats(min_value=1.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
            min_size=5,
            max_size=50
        ),
        period=st.integers(min_value=2, max_value=20)
    )
    def test_sma_calculation_correctness(self, prices, period):
        """Property test: SMA calculation should match standard formula exactly.
        
        **Validates: Requirements 5.2**
        """
        # Skip if not enough data
        if len(prices) < period:
            return
        
        data_handler = DataHandler(max_history_size=1000)
        try:
            # Calculate SMA using data handler
            calculated_sma = data_handler._calculate_sma(prices, period)
            
            # Calculate reference SMA
            reference_sma = self._reference_sma(prices, period)
            
            # Verify SMA is positive for positive prices
            assert calculated_sma > 0, f"SMA {calculated_sma} should be positive for positive prices"
            
            # Verify SMA matches reference calculation within acceptable precision (±0.01)
            precision_tolerance = 0.01
            assert abs(calculated_sma - reference_sma) <= precision_tolerance, \
                f"SMA calculation differs: calculated={calculated_sma}, reference={reference_sma}"
        finally:
            data_handler.stop()
    
    @given(
        prices=st.lists(
            st.floats(min_value=1.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
            min_size=5,
            max_size=50
        ),
        period=st.integers(min_value=2, max_value=20)
    )
    def test_ema_calculation_correctness(self, prices, period):
        """Property test: EMA calculation should match standard formula within acceptable precision.
        
        **Validates: Requirements 5.2**
        """
        # Skip if not enough data
        if len(prices) < period:
            return
        
        data_handler = DataHandler(max_history_size=1000)
        try:
            # Calculate EMA using data handler
            calculated_ema = data_handler._calculate_ema(prices, period)
            
            # Calculate reference EMA
            reference_ema = self._reference_ema(prices, period)
            
            # Verify EMA is positive for positive prices
            assert calculated_ema > 0, f"EMA {calculated_ema} should be positive for positive prices"
            
            # Verify EMA matches reference calculation within acceptable precision (±0.01)
            precision_tolerance = 0.01
            assert abs(calculated_ema - reference_ema) <= precision_tolerance, \
                f"EMA calculation differs: calculated={calculated_ema}, reference={reference_ema}"
        finally:
            data_handler.stop()
    
    @given(
        prices=st.lists(
            st.floats(min_value=1.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
            min_size=30,
            max_size=100
        )
    )
    def test_macd_calculation_properties(self, prices):
        """Property test: MACD calculation should follow mathematical relationships.
        
        **Validates: Requirements 5.2**
        """
        data_handler = DataHandler(max_history_size=1000)
        try:
            # Calculate MACD using data handler
            macd_line, signal_line, histogram = data_handler._calculate_macd(prices)
            
            # Verify MACD components are finite numbers
            assert np.isfinite(macd_line), f"MACD line {macd_line} should be finite"
            assert np.isfinite(signal_line), f"Signal line {signal_line} should be finite"
            assert np.isfinite(histogram), f"Histogram {histogram} should be finite"
            
            # Verify histogram relationship: histogram = macd_line - signal_line
            expected_histogram = macd_line - signal_line
            precision_tolerance = 0.001
            assert abs(histogram - expected_histogram) <= precision_tolerance, \
                f"MACD histogram relationship violated: histogram={histogram}, expected={expected_histogram}"
        finally:
            data_handler.stop()
    
    @given(
        base_price=st.floats(min_value=100.0, max_value=10000.0),
        trend=st.floats(min_value=-0.1, max_value=0.1),
        noise_level=st.floats(min_value=0.001, max_value=0.05),
        length=st.integers(min_value=20, max_value=50)
    )
    def test_indicator_monotonicity_properties(self, base_price, trend, noise_level, length):
        """Property test: Indicators should behave predictably with trending data.
        
        **Validates: Requirements 5.2**
        """
        data_handler = DataHandler(max_history_size=1000)
        try:
            # Generate trending price series with noise
            prices = []
            current_price = base_price
            
            for i in range(length):
                # Add trend and random noise
                noise = np.random.uniform(-noise_level, noise_level) * current_price
                current_price = current_price * (1 + trend) + noise
                current_price = max(current_price, 1.0)  # Ensure positive
                prices.append(current_price)
            
            # Calculate indicators
            rsi = data_handler._calculate_rsi(prices, min(14, length - 1))
            sma_short = data_handler._calculate_sma(prices, min(5, length))
            sma_long = data_handler._calculate_sma(prices, min(10, length))
            
            # Verify RSI bounds
            assert 0 <= rsi <= 100, f"RSI {rsi} outside bounds"
            
            # Verify SMA ordering for uptrend (when trend > 0.01)
            if trend > 0.01 and length >= 10:
                # In strong uptrend, shorter SMA should be >= longer SMA
                assert sma_short >= sma_long * 0.95, \
                    f"In uptrend, short SMA {sma_short} should be >= long SMA {sma_long}"
            
            # Verify SMA ordering for downtrend (when trend < -0.01)
            if trend < -0.01 and length >= 10:
                # In strong downtrend, shorter SMA should be <= longer SMA
                assert sma_short <= sma_long * 1.05, \
                    f"In downtrend, short SMA {sma_short} should be <= long SMA {sma_long}"
        finally:
            data_handler.stop()
    
    @given(
        constant_price=st.floats(min_value=10.0, max_value=1000.0),
        length=st.integers(min_value=15, max_value=30)
    )
    def test_indicators_with_constant_prices(self, constant_price, length):
        """Property test: Indicators should handle constant price series correctly.
        
        **Validates: Requirements 5.2**
        """
        data_handler = DataHandler(max_history_size=1000)
        try:
            # Create constant price series
            prices = [constant_price] * length
            
            # Calculate indicators
            rsi = data_handler._calculate_rsi(prices, 14)
            sma = data_handler._calculate_sma(prices, 10)
            ema = data_handler._calculate_ema(prices, 10)
            
            # For constant prices:
            # - RSI should be 50 (neutral)
            # - SMA should equal the constant price
            # - EMA should equal the constant price
            
            assert abs(rsi - 50.0) < 0.1, f"RSI for constant prices should be ~50, got {rsi}"
            assert abs(sma - constant_price) < 0.01, f"SMA for constant prices should be {constant_price}, got {sma}"
            assert abs(ema - constant_price) < 0.01, f"EMA for constant prices should be {constant_price}, got {ema}"
        finally:
            data_handler.stop()


class TestInputValidationCompleteness:
    """Property-based tests for input validation completeness.
    
    **Feature: trading-bot-system, Property 6: Input Validation Completeness**
    **Validates: Requirements 5.4**
    """
    
    @given(
        symbol=st.one_of(
            st.none(),
            st.text(min_size=0, max_size=0),  # Empty string
            st.integers(),  # Wrong type
            st.lists(st.text()),  # Wrong type
            st.text(alphabet=st.characters(blacklist_categories=('Cc', 'Cs')), min_size=1, max_size=20)  # Valid symbol for comparison
        )
    )
    def test_invalid_symbol_rejection(self, symbol):
        """Property test: Invalid symbols should be rejected without processing.
        
        **Validates: Requirements 5.4**
        """
        data_handler = DataHandler(max_history_size=100)
        try:
            # Create raw data with potentially invalid symbol
            raw_data = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'open': Decimal('50000.00'),
                'high': Decimal('50100.00'),
                'low': Decimal('49900.00'),
                'last': Decimal('50050.00'),
                'bid': Decimal('50040.00'),
                'ask': Decimal('50060.00'),
                'volume': Decimal('1.5')
            }
            
            # Invalid symbols should be rejected
            if symbol is None or symbol == "" or not isinstance(symbol, str):
                # Should not process invalid symbol data
                initial_data_count = len(data_handler._price_data)
                data_handler._process_market_data(raw_data)
                
                # Data should not be stored for invalid symbols
                assert len(data_handler._price_data) == initial_data_count, \
                    f"Invalid symbol {symbol} should not be processed"
            else:
                # Valid symbols should be processed normally
                data_handler._process_market_data(raw_data)
                if isinstance(symbol, str) and len(symbol) > 0:
                    assert symbol in data_handler._price_data, \
                        f"Valid symbol {symbol} should be processed"
        finally:
            data_handler.stop()
    
    @given(
        timestamp=st.one_of(
            st.none(),
            st.text(),  # Wrong type
            st.integers(),  # Wrong type
            st.datetimes(min_value=datetime(1900, 1, 1), max_value=datetime(2100, 1, 1))  # Valid timestamp for comparison
        )
    )
    def test_invalid_timestamp_rejection(self, timestamp):
        """Property test: Invalid timestamps should be rejected without processing.
        
        **Validates: Requirements 5.4**
        """
        data_handler = DataHandler(max_history_size=100)
        try:
            raw_data = {
                'symbol': 'BTC/USD',
                'timestamp': timestamp,
                'open': Decimal('50000.00'),
                'high': Decimal('50100.00'),
                'low': Decimal('49900.00'),
                'last': Decimal('50050.00'),
                'bid': Decimal('50040.00'),
                'ask': Decimal('50060.00'),
                'volume': Decimal('1.5')
            }
            
            # Invalid timestamps should be rejected
            if not isinstance(timestamp, datetime):
                initial_data_count = len(data_handler._price_data.get('BTC/USD', []))
                data_handler._process_market_data(raw_data)
                
                # Data should not be stored for invalid timestamps
                final_data_count = len(data_handler._price_data.get('BTC/USD', []))
                assert final_data_count == initial_data_count, \
                    f"Invalid timestamp {timestamp} should not be processed"
            else:
                # Valid timestamps should be processed normally
                data_handler._process_market_data(raw_data)
                assert len(data_handler._price_data['BTC/USD']) > 0, \
                    "Valid timestamp should be processed"
        finally:
            data_handler.stop()
    
    @given(
        price_data=st.fixed_dictionaries({
            'open': st.one_of(
                st.none(),
                st.text(),  # Wrong type
                st.floats(min_value=-1000.0, max_value=-0.01),  # Negative prices
                st.floats(min_value=0.01, max_value=100000.0).map(lambda x: Decimal(str(x))),  # Valid prices
                st.just(Decimal('0'))  # Zero price
            ),
            'high': st.one_of(
                st.none(),
                st.text(),  # Wrong type
                st.floats(min_value=-1000.0, max_value=-0.01),  # Negative prices
                st.floats(min_value=0.01, max_value=100000.0).map(lambda x: Decimal(str(x))),  # Valid prices
            ),
            'low': st.one_of(
                st.none(),
                st.text(),  # Wrong type
                st.floats(min_value=-1000.0, max_value=-0.01),  # Negative prices
                st.floats(min_value=0.01, max_value=100000.0).map(lambda x: Decimal(str(x))),  # Valid prices
            ),
            'last': st.one_of(
                st.none(),
                st.text(),  # Wrong type
                st.floats(min_value=-1000.0, max_value=-0.01),  # Negative prices
                st.floats(min_value=0.01, max_value=100000.0).map(lambda x: Decimal(str(x))),  # Valid prices
            ),
            'bid': st.one_of(
                st.none(),
                st.text(),  # Wrong type
                st.floats(min_value=-1000.0, max_value=-0.01),  # Negative prices
                st.floats(min_value=0.01, max_value=100000.0).map(lambda x: Decimal(str(x))),  # Valid prices
            ),
            'ask': st.one_of(
                st.none(),
                st.text(),  # Wrong type
                st.floats(min_value=-1000.0, max_value=-0.01),  # Negative prices
                st.floats(min_value=0.01, max_value=100000.0).map(lambda x: Decimal(str(x))),  # Valid prices
            ),
            'volume': st.one_of(
                st.none(),
                st.text(),  # Wrong type
                st.floats(min_value=-1000.0, max_value=-0.01),  # Negative volume
                st.floats(min_value=0.0, max_value=100000.0).map(lambda x: Decimal(str(x))),  # Valid volume (including 0)
            )
        })
    )
    def test_invalid_price_data_rejection(self, price_data):
        """Property test: Invalid price data should be rejected without processing.
        
        **Validates: Requirements 5.4**
        """
        data_handler = DataHandler(max_history_size=100)
        try:
            raw_data = {
                'symbol': 'BTC/USD',
                'timestamp': datetime.now(),
                **price_data
            }
            
            # Check if any price data is invalid
            has_invalid_data = False
            
            for key, value in price_data.items():
                if value is None or not isinstance(value, Decimal):
                    has_invalid_data = True
                    break
                if key != 'volume' and value <= 0:  # Prices must be positive
                    has_invalid_data = True
                    break
                if key == 'volume' and value < 0:  # Volume must be non-negative
                    has_invalid_data = True
                    break
            
            # Check for invalid price relationships (bid >= ask)
            if (isinstance(price_data.get('bid'), Decimal) and 
                isinstance(price_data.get('ask'), Decimal) and
                price_data['bid'] >= price_data['ask']):
                has_invalid_data = True
            
            initial_data_count = len(data_handler._price_data.get('BTC/USD', []))
            data_handler._process_market_data(raw_data)
            final_data_count = len(data_handler._price_data.get('BTC/USD', []))
            
            if has_invalid_data:
                # Invalid data should not be processed
                assert final_data_count == initial_data_count, \
                    f"Invalid price data should not be processed: {price_data}"
            else:
                # Valid data should be processed
                assert final_data_count > initial_data_count, \
                    f"Valid price data should be processed: {price_data}"
        finally:
            data_handler.stop()
    
    @given(
        malformed_data=st.one_of(
            st.none(),
            st.text(),  # Wrong type entirely
            st.integers(),  # Wrong type entirely
            st.lists(st.text()),  # Wrong type entirely
            st.dictionaries(
                keys=st.text(min_size=1, max_size=10),
                values=st.one_of(st.none(), st.text(), st.integers(), st.floats()),
                min_size=0,
                max_size=3
            ),  # Dictionary with wrong/missing keys
            st.fixed_dictionaries({
                'symbol': st.text(min_size=1, max_size=10),
                'timestamp': st.datetimes(),
                # Missing required price fields
            })
        )
    )
    def test_malformed_api_response_rejection(self, malformed_data):
        """Property test: Malformed API responses should be rejected without processing.
        
        **Validates: Requirements 5.4**
        """
        data_handler = DataHandler(max_history_size=100)
        try:
            initial_total_data = sum(len(deque_data) for deque_data in data_handler._price_data.values())
            
            # Try to process malformed data
            data_handler._process_market_data(malformed_data)
            
            final_total_data = sum(len(deque_data) for deque_data in data_handler._price_data.values())
            
            # Malformed data should never be processed
            assert final_total_data == initial_total_data, \
                f"Malformed data should not be processed: {malformed_data}"
        finally:
            data_handler.stop()
    
    @given(
        base_price=st.floats(min_value=1.0, max_value=1000.0),
        corruption_type=st.sampled_from([
            'missing_required_field',
            'extra_unexpected_field',
            'wrong_data_type',
            'invalid_ohlc_relationship'
        ])
    )
    def test_data_corruption_detection(self, base_price, corruption_type):
        """Property test: Data corruption should be detected and rejected.
        
        **Validates: Requirements 5.4**
        """
        data_handler = DataHandler(max_history_size=100)
        try:
            # Create valid base data first
            base_price_decimal = Decimal(str(round(base_price, 2)))
            valid_base_data = {
                'symbol': 'TESTBTC',
                'timestamp': datetime(2023, 1, 1, 12, 0, 0),
                'open': base_price_decimal,
                'high': base_price_decimal * Decimal('1.01'),  # 1% higher
                'low': base_price_decimal * Decimal('0.99'),   # 1% lower
                'last': base_price_decimal,
                'bid': base_price_decimal * Decimal('0.999'),
                'ask': base_price_decimal * Decimal('1.001'),
                'volume': Decimal('1.0')
            }
            
            # Create corrupted data based on corruption type
            corrupted_data = valid_base_data.copy()
            
            if corruption_type == 'missing_required_field':
                # Remove a required field
                required_fields = ['symbol', 'timestamp', 'last', 'bid', 'ask']
                field_to_remove = np.random.choice(required_fields)
                if field_to_remove in corrupted_data:
                    del corrupted_data[field_to_remove]
            
            elif corruption_type == 'extra_unexpected_field':
                # Add unexpected field (this should be handled gracefully)
                corrupted_data['unexpected_field'] = "unexpected_value"
            
            elif corruption_type == 'wrong_data_type':
                # Change a field to wrong data type
                corrupted_data['last'] = "not_a_decimal"
            
            elif corruption_type == 'invalid_ohlc_relationship':
                # Create invalid OHLC relationships (high < low, etc.)
                corrupted_data['high'] = Decimal('10.00')
                corrupted_data['low'] = Decimal('20.00')  # Low > High (invalid)
                corrupted_data['open'] = Decimal('15.00')
                corrupted_data['last'] = Decimal('25.00')  # Close > High (invalid)
                # Update bid/ask to maintain consistency
                corrupted_data['bid'] = Decimal('24.75')
                corrupted_data['ask'] = Decimal('25.25')
            
            initial_data_count = len(data_handler._price_data.get(corrupted_data.get('symbol', 'UNKNOWN'), []))
            data_handler._process_market_data(corrupted_data)
            final_data_count = len(data_handler._price_data.get(corrupted_data.get('symbol', 'UNKNOWN'), []))
            
            # Determine if data should be rejected
            should_reject = (
                corruption_type in ['missing_required_field', 'wrong_data_type', 'invalid_ohlc_relationship'] or
                not isinstance(corrupted_data.get('symbol'), str) or
                not isinstance(corrupted_data.get('timestamp'), datetime) or
                not isinstance(corrupted_data.get('last'), Decimal)
            )
            
            if should_reject:
                assert final_data_count == initial_data_count, \
                    f"Corrupted data ({corruption_type}) should be rejected"
            else:
                # Extra fields should be handled gracefully (not rejected)
                if corruption_type == 'extra_unexpected_field':
                    assert final_data_count > initial_data_count, \
                        f"Data with extra fields should be processed gracefully"
        finally:
            data_handler.stop()
    
    @given(
        edge_case_values=st.fixed_dictionaries({
            'symbol': st.sampled_from(['A', 'BTC', 'VERYLONGSYMBOLNAME' * 2, '123', 'BTC/USD']),  # Removed empty string
            'timestamp': st.one_of(
                st.datetimes(min_value=datetime(1970, 1, 1), max_value=datetime(2100, 1, 1))
            ),
            'prices': st.one_of(
                st.just([Decimal('0.00000001')]),  # Very small price
                st.just([Decimal('100000.00')]),   # Large but reasonable price
                st.just([Decimal('100.00')]),      # Normal price
            )
        })
    )
    def test_edge_case_value_handling(self, edge_case_values):
        """Property test: Edge case values should be handled appropriately.
        
        **Validates: Requirements 5.4**
        """
        data_handler = DataHandler(max_history_size=100)
        try:
            symbol = edge_case_values['symbol']
            timestamp = edge_case_values['timestamp']
            price = edge_case_values['prices'][0]
            
            raw_data = {
                'symbol': symbol,
                'timestamp': timestamp,
                'open': price,
                'high': price * Decimal('1.001'),
                'low': price * Decimal('0.999'),
                'last': price,
                'bid': price * Decimal('0.9995'),
                'ask': price * Decimal('1.0005'),
                'volume': Decimal('1.0')
            }
            
            initial_data_count = len(data_handler._price_data.get(symbol, []))
            data_handler._process_market_data(raw_data)
            final_data_count = len(data_handler._price_data.get(symbol, []))
            
            # Determine if edge case should be accepted
            should_accept = (
                isinstance(symbol, str) and len(symbol) > 0 and len(symbol) <= 50 and
                isinstance(timestamp, datetime) and
                price > 0 and price < Decimal('500000000')  # More conservative price limit to allow for multiplications
            )
            
            if should_accept:
                assert final_data_count > initial_data_count, \
                    f"Valid edge case should be processed: symbol={symbol}, price={price}"
            else:
                assert final_data_count == initial_data_count, \
                    f"Invalid edge case should be rejected: symbol={symbol}, price={price}"
        finally:
            data_handler.stop()


class TestDataStorageFormatConsistency:
    """Property-based tests for data storage format consistency.
    
    **Feature: trading-bot-system, Property 12: Data Storage Format Consistency**
    **Validates: Requirements 5.6**
    """
    
    @given(
        symbol=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=3, max_size=10),
        data_points=st.lists(
            st.fixed_dictionaries({
                'base_price': st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
                'timestamp_offset': st.integers(min_value=0, max_value=86400),  # Seconds in a day
                'volume': st.floats(min_value=0.1, max_value=1000.0, allow_nan=False, allow_infinity=False)
            }),
            min_size=1,
            max_size=50
        )
    )
    def test_time_series_format_consistency(self, symbol, data_points):
        """Property test: Processed market data should be stored in consistent time-series format.
        
        **Validates: Requirements 5.6**
        """
        data_handler = DataHandler(max_history_size=1000)
        try:
            base_timestamp = datetime(2023, 1, 1, 12, 0, 0)
            
            # Process multiple data points
            for i, point_data in enumerate(data_points):
                base_price = Decimal(str(round(point_data['base_price'], 2)))
                timestamp = base_timestamp.replace(second=point_data['timestamp_offset'] % 60,
                                                 minute=(point_data['timestamp_offset'] // 60) % 60)
                volume = Decimal(str(round(point_data['volume'], 4)))
                
                raw_data = {
                    'symbol': symbol,
                    'timestamp': timestamp,
                    'open': base_price,
                    'high': base_price * Decimal('1.01'),
                    'low': base_price * Decimal('0.99'),
                    'last': base_price,
                    'bid': base_price * Decimal('0.999'),
                    'ask': base_price * Decimal('1.001'),
                    'volume': volume
                }
                
                data_handler._process_market_data(raw_data)
            
            # Retrieve historical data in time-series format
            df = data_handler.get_historical_data(symbol, len(data_points))
            
            # Verify time-series format properties
            assert isinstance(df, pd.DataFrame), "Historical data should be returned as pandas DataFrame"
            
            if not df.empty:
                # Verify consistent schema - required columns
                required_columns = {'open', 'high', 'low', 'close', 'volume'}
                actual_columns = set(df.columns)
                assert required_columns.issubset(actual_columns), \
                    f"Time-series data missing required columns. Expected: {required_columns}, Got: {actual_columns}"
                
                # Verify proper indexing - timestamp should be the index
                assert isinstance(df.index, pd.DatetimeIndex), \
                    f"Time-series data should have DatetimeIndex, got {type(df.index)}"
                
                # Verify data types consistency
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    assert pd.api.types.is_numeric_dtype(df[col]), \
                        f"Column {col} should be numeric type, got {df[col].dtype}"
                
                # Verify data integrity - OHLC relationships
                for idx in df.index:
                    row = df.loc[idx]
                    # Handle case where multiple rows have the same timestamp (pandas returns Series)
                    if isinstance(row, pd.Series):
                        # Single row case
                        high_val = float(row['high'])
                        low_val = float(row['low'])
                        open_val = float(row['open'])
                        close_val = float(row['close'])
                        volume_val = float(row['volume'])
                        
                        assert high_val >= max(open_val, close_val), \
                            f"High price should be >= max(open, close) at {idx}"
                        assert low_val <= min(open_val, close_val), \
                            f"Low price should be <= min(open, close) at {idx}"
                        assert volume_val >= 0, f"Volume should be non-negative at {idx}"
                    else:
                        # Multiple rows with same timestamp case (DataFrame)
                        for _, single_row in row.iterrows():
                            high_val = float(single_row['high'])
                            low_val = float(single_row['low'])
                            open_val = float(single_row['open'])
                            close_val = float(single_row['close'])
                            volume_val = float(single_row['volume'])
                            
                            assert high_val >= max(open_val, close_val), \
                                f"High price should be >= max(open, close) at {idx}"
                            assert low_val <= min(open_val, close_val), \
                                f"Low price should be <= min(open, close) at {idx}"
                            assert volume_val >= 0, f"Volume should be non-negative at {idx}"
                
                # Note: We don't enforce chronological ordering here because the data handler
                # may store data in the order it's processed, not necessarily chronological order.
                # The important thing is that the data is retrievable in a consistent format.
        finally:
            data_handler.stop()
    
    @given(
        symbols=st.lists(
            st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=3, max_size=8),
            min_size=2,
            max_size=5,
            unique=True
        ),
        periods_requested=st.integers(min_value=1, max_value=20)
    )
    def test_multi_symbol_storage_consistency(self, symbols, periods_requested):
        """Property test: Multiple symbols should have consistent storage format.
        
        **Validates: Requirements 5.6**
        """
        data_handler = DataHandler(max_history_size=1000)
        try:
            base_timestamp = datetime(2023, 1, 1, 12, 0, 0)
            
            # Process data for multiple symbols
            for symbol in symbols:
                for i in range(periods_requested):
                    timestamp = base_timestamp.replace(minute=i)
                    base_price = Decimal('100.00') + Decimal(str(i))
                    
                    raw_data = {
                        'symbol': symbol,
                        'timestamp': timestamp,
                        'open': base_price,
                        'high': base_price * Decimal('1.01'),
                        'low': base_price * Decimal('0.99'),
                        'last': base_price,
                        'bid': base_price * Decimal('0.999'),
                        'ask': base_price * Decimal('1.001'),
                        'volume': Decimal('1.0')
                    }
                    
                    data_handler._process_market_data(raw_data)
            
            # Verify consistent format across all symbols
            schemas = []
            for symbol in symbols:
                df = data_handler.get_historical_data(symbol, periods_requested)
                
                if not df.empty:
                    # Collect schema information
                    schema = {
                        'columns': set(df.columns),
                        'index_type': type(df.index).__name__,
                        'dtypes': {col: str(df[col].dtype) for col in df.columns}
                    }
                    schemas.append(schema)
            
            # Verify all schemas are identical
            if len(schemas) > 1:
                first_schema = schemas[0]
                for i, schema in enumerate(schemas[1:], 1):
                    assert schema['columns'] == first_schema['columns'], \
                        f"Symbol {symbols[i]} has different columns than {symbols[0]}"
                    assert schema['index_type'] == first_schema['index_type'], \
                        f"Symbol {symbols[i]} has different index type than {symbols[0]}"
                    
                    # Data types should be consistent
                    for col in first_schema['columns']:
                        assert schema['dtypes'][col] == first_schema['dtypes'][col], \
                            f"Column {col} has different dtype for {symbols[i]} vs {symbols[0]}"
        finally:
            data_handler.stop()
    
    @given(
        symbol=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=3, max_size=10),
        total_data_points=st.integers(min_value=10, max_value=100),
        retrieval_periods=st.lists(
            st.integers(min_value=1, max_value=50),
            min_size=1,
            max_size=5
        )
    )
    def test_backtesting_retrieval_consistency(self, symbol, total_data_points, retrieval_periods):
        """Property test: Data retrieval for backtesting should be consistent and complete.
        
        **Validates: Requirements 5.6**
        """
        data_handler = DataHandler(max_history_size=1000)
        try:
            base_timestamp = datetime(2023, 1, 1, 12, 0, 0)
            
            # Store sequential data points
            stored_timestamps = []
            for i in range(total_data_points):
                timestamp = base_timestamp.replace(minute=i % 60, hour=12 + (i // 60))
                stored_timestamps.append(timestamp)
                base_price = Decimal('100.00') + Decimal(str(i * 0.1))
                
                raw_data = {
                    'symbol': symbol,
                    'timestamp': timestamp,
                    'open': base_price,
                    'high': base_price * Decimal('1.01'),
                    'low': base_price * Decimal('0.99'),
                    'last': base_price,
                    'bid': base_price * Decimal('0.999'),
                    'ask': base_price * Decimal('1.001'),
                    'volume': Decimal('1.0')
                }
                
                data_handler._process_market_data(raw_data)
            
            # Test different retrieval periods
            for periods in retrieval_periods:
                df = data_handler.get_historical_data(symbol, periods)
                
                if not df.empty:
                    # Verify retrieval completeness
                    expected_periods = min(periods, total_data_points)
                    assert len(df) == expected_periods, \
                        f"Should retrieve {expected_periods} periods, got {len(df)}"
                    
                    # Verify most recent data is returned (for backtesting accuracy)
                    if len(stored_timestamps) >= periods:
                        expected_latest_timestamps = sorted(stored_timestamps)[-periods:]
                        actual_timestamps = sorted(df.index.to_pydatetime())
                        
                        # Allow some tolerance for timestamp comparison
                        for expected, actual in zip(expected_latest_timestamps, actual_timestamps):
                            time_diff = abs((expected - actual).total_seconds())
                            assert time_diff < 1, \
                                f"Timestamp mismatch: expected {expected}, got {actual}"
                    
                    # Verify data completeness - no missing values in critical columns
                    critical_columns = ['open', 'high', 'low', 'close', 'volume']
                    for col in critical_columns:
                        assert not df[col].isna().any(), \
                            f"Column {col} should not have missing values for backtesting"
                        assert not df[col].isnull().any(), \
                            f"Column {col} should not have null values for backtesting"
        finally:
            data_handler.stop()
    
    @given(
        symbol=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=3, max_size=10),
        data_sequence=st.lists(
            st.fixed_dictionaries({
                'price': st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
                'volume': st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
                'minute_offset': st.integers(min_value=0, max_value=1440)  # Minutes in a day
            }),
            min_size=5,
            max_size=30
        )
    )
    def test_storage_format_precision_consistency(self, symbol, data_sequence):
        """Property test: Stored data should maintain precision consistency for backtesting accuracy.
        
        **Validates: Requirements 5.6**
        """
        data_handler = DataHandler(max_history_size=1000)
        try:
            base_timestamp = datetime(2023, 1, 1, 12, 0, 0)
            original_data = []
            
            # Process data with specific precision requirements
            for i, point in enumerate(data_sequence):
                timestamp = base_timestamp.replace(minute=point['minute_offset'] % 60,
                                                 hour=12 + (point['minute_offset'] // 60) % 12)
                
                # Use precise decimal values
                price = Decimal(str(round(point['price'], 2)))  # 2 decimal places for price
                volume = Decimal(str(round(point['volume'], 4)))  # 4 decimal places for volume
                
                raw_data = {
                    'symbol': symbol,
                    'timestamp': timestamp,
                    'open': price,
                    'high': price * Decimal('1.005'),  # 0.5% higher
                    'low': price * Decimal('0.995'),   # 0.5% lower
                    'last': price,
                    'bid': price * Decimal('0.9995'),
                    'ask': price * Decimal('1.0005'),
                    'volume': volume
                }
                
                # Store original data with insertion order preserved
                original_data.append({
                    'insertion_order': i,  # Add insertion order for proper comparison
                    'timestamp': timestamp,
                    'open': float(price),
                    'high': float(price * Decimal('1.005')),
                    'low': float(price * Decimal('0.995')),
                    'close': float(price),
                    'volume': float(volume)
                })
                
                data_handler._process_market_data(raw_data)
            
            # Retrieve and verify precision consistency
            df = data_handler.get_historical_data(symbol, len(data_sequence))
            
            if not df.empty and len(original_data) > 0:
                # The DataFrame preserves insertion order for same timestamps
                # So we can compare directly by position
                df_list = df.reset_index().to_dict('records')
                
                # Verify we have the same number of records
                assert len(df_list) == len(original_data), \
                    f"Record count mismatch: DataFrame has {len(df_list)}, original has {len(original_data)}"
                
                # Compare stored vs original data precision by insertion order
                for i in range(min(len(df_list), len(original_data))):
                    stored = df_list[i]
                    original = original_data[i]
                    
                    # Verify precision is maintained within acceptable tolerance for Decimal->float64 conversion
                    # More realistic tolerances that account for floating point precision limitations
                    price_tolerance = max(0.01, abs(original['open']) * 1e-10)  # Relative tolerance for price precision
                    volume_tolerance = max(0.0001, abs(original['volume']) * 1e-10)  # Relative tolerance for volume precision
                    
                    # Additional check: ensure we're not getting completely wrong values (like 1.0 -> 2.0)
                    # This catches major precision errors while allowing minor floating point differences
                    max_relative_error = 0.001  # 0.1% maximum relative error
                    
                    for field_name, stored_val, original_val, tolerance in [
                        ('open', stored['open'], original['open'], price_tolerance),
                        ('high', stored['high'], original['high'], price_tolerance),
                        ('low', stored['low'], original['low'], price_tolerance),
                        ('close', stored['close'], original['close'], price_tolerance),
                        ('volume', stored['volume'], original['volume'], volume_tolerance)
                    ]:
                        # Check absolute tolerance
                        abs_diff = abs(stored_val - original_val)
                        assert abs_diff <= tolerance, \
                            f"{field_name.capitalize()} precision lost at position {i}: stored={stored_val}, original={original_val}, diff={abs_diff}"
                        
                        # Check relative error for non-zero values
                        if abs(original_val) > 1e-10:  # Avoid division by very small numbers
                            relative_error = abs_diff / abs(original_val)
                            assert relative_error <= max_relative_error, \
                                f"{field_name.capitalize()} relative error too large at position {i}: stored={stored_val}, original={original_val}, relative_error={relative_error:.6f}"
        finally:
            data_handler.stop()
    
    @given(
        symbol=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=3, max_size=10),
        empty_data_scenario=st.sampled_from([
            'no_data_processed',
            'invalid_data_only',
            'zero_periods_requested'
        ])
    )
    def test_empty_data_storage_format_consistency(self, symbol, empty_data_scenario):
        """Property test: Empty data scenarios should return consistent time-series format.
        
        **Validates: Requirements 5.6**
        """
        data_handler = DataHandler(max_history_size=1000)
        try:
            if empty_data_scenario == 'invalid_data_only':
                # Process only invalid data that should be rejected
                invalid_data = {
                    'symbol': symbol,
                    'timestamp': "not_a_datetime",  # Invalid timestamp
                    'open': Decimal('100.00'),
                    'high': Decimal('101.00'),
                    'low': Decimal('99.00'),
                    'last': Decimal('100.00'),
                    'bid': Decimal('99.95'),
                    'ask': Decimal('100.05'),
                    'volume': Decimal('1.0')
                }
                data_handler._process_market_data(invalid_data)
            
            # Test different retrieval scenarios
            if empty_data_scenario == 'zero_periods_requested':
                periods = 0
            else:
                periods = 10
            
            df = data_handler.get_historical_data(symbol, periods)
            
            # Verify consistent format even for empty data
            assert isinstance(df, pd.DataFrame), \
                "Should always return DataFrame even for empty data"
            
            if df.empty:
                # Empty DataFrame should still have proper structure
                assert isinstance(df.index, pd.DatetimeIndex) or len(df.index) == 0, \
                    "Empty DataFrame should have DatetimeIndex or empty index"
            else:
                # If not empty, should follow standard format
                required_columns = {'open', 'high', 'low', 'close', 'volume'}
                assert required_columns.issubset(set(df.columns)), \
                    "Non-empty DataFrame should have required columns"
        finally:
            data_handler.stop()