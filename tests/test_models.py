"""Unit tests for core data models."""

import pytest
from datetime import datetime
from decimal import Decimal
from hypothesis import given, strategies as st

from trading_bot.models import (
    Price, MarketData, TradingSignal, Position, OrderRequest, OHLCV,
    SignalDirection, OrderSide, OrderType, TimeInForce
)


class TestPrice:
    """Test Price model."""
    
    def test_price_creation(self, sample_price):
        """Test price model creation."""
        assert sample_price.symbol == "BTC/USD"
        assert isinstance(sample_price.bid, Decimal)
        assert isinstance(sample_price.ask, Decimal)
        assert isinstance(sample_price.last, Decimal)
        assert isinstance(sample_price.volume, Decimal)
        assert isinstance(sample_price.timestamp, datetime)
    
    @given(
        symbol=st.text(min_size=3, max_size=10),
        bid=st.decimals(min_value=0, max_value=1000000, places=2),
        ask=st.decimals(min_value=0, max_value=1000000, places=2),
        last=st.decimals(min_value=0, max_value=1000000, places=2),
        volume=st.decimals(min_value=0, max_value=1000000, places=2)
    )
    def test_price_property_valid_values(self, symbol, bid, ask, last, volume):
        """Property test: Price should accept valid decimal values."""
        price = Price(
            symbol=symbol,
            timestamp=datetime.now(),
            bid=bid,
            ask=ask,
            last=last,
            volume=volume
        )
        assert price.bid >= 0
        assert price.ask >= 0
        assert price.last >= 0
        assert price.volume >= 0


class TestMarketData:
    """Test MarketData model."""
    
    def test_market_data_creation(self, sample_market_data):
        """Test market data model creation."""
        assert sample_market_data.symbol == "BTC/USD"
        assert isinstance(sample_market_data.ohlcv, OHLCV)
        assert isinstance(sample_market_data.indicators, dict)
        assert "RSI" in sample_market_data.indicators
        assert "SMA_20" in sample_market_data.indicators


class TestTradingSignal:
    """Test TradingSignal model."""
    
    def test_trading_signal_creation(self, sample_trading_signal):
        """Test trading signal model creation."""
        assert sample_trading_signal.symbol == "BTC/USD"
        assert sample_trading_signal.direction == SignalDirection.BUY
        assert 0.0 <= sample_trading_signal.strength <= 1.0
        assert 0.0 <= sample_trading_signal.confidence <= 1.0
        assert sample_trading_signal.strategy == "scalping"
    
    @given(
        strength=st.floats(min_value=0.0, max_value=1.0),
        confidence=st.floats(min_value=0.0, max_value=1.0)
    )
    def test_signal_strength_confidence_bounds(self, strength, confidence):
        """Property test: Signal strength and confidence should be between 0 and 1."""
        signal = TradingSignal(
            symbol="TEST/USD",
            direction=SignalDirection.BUY,
            strength=strength,
            confidence=confidence,
            timestamp=datetime.now(),
            strategy="test",
            metadata={}
        )
        assert 0.0 <= signal.strength <= 1.0
        assert 0.0 <= signal.confidence <= 1.0


class TestOrderRequest:
    """Test OrderRequest model."""
    
    def test_order_request_creation(self):
        """Test order request model creation."""
        order = OrderRequest(
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
            price=None,
            stop_loss=Decimal("49000.00"),
            take_profit=Decimal("51000.00"),
            time_in_force=TimeInForce.GTC
        )
        assert order.symbol == "BTC/USD"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET
        assert order.quantity == Decimal("0.1")
        assert order.price is None
        assert order.stop_loss == Decimal("49000.00")
        assert order.take_profit == Decimal("51000.00")
        assert order.time_in_force == TimeInForce.GTC