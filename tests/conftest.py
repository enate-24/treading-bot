"""Pytest configuration and fixtures."""

import pytest
from datetime import datetime
from decimal import Decimal
from hypothesis import settings

# Configure Hypothesis for property-based testing
settings.register_profile("default", max_examples=20, deadline=None)  # Reduced for faster execution
settings.load_profile("default")


@pytest.fixture
def sample_price():
    """Sample price data for testing."""
    from trading_bot.models import Price
    return Price(
        symbol="BTC/USD",
        timestamp=datetime.now(),
        bid=Decimal("50000.00"),
        ask=Decimal("50001.00"),
        last=Decimal("50000.50"),
        volume=Decimal("100.0")
    )


@pytest.fixture
def sample_market_data():
    """Sample market data for testing."""
    from trading_bot.models import MarketData, OHLCV
    return MarketData(
        symbol="BTC/USD",
        timestamp=datetime.now(),
        ohlcv=OHLCV(
            open=Decimal("49900.00"),
            high=Decimal("50100.00"),
            low=Decimal("49800.00"),
            close=Decimal("50000.00"),
            volume=Decimal("1000.0")
        ),
        indicators={"RSI": 65.5, "SMA_20": 49950.0}
    )


@pytest.fixture
def sample_trading_signal():
    """Sample trading signal for testing."""
    from trading_bot.models import TradingSignal, SignalDirection
    return TradingSignal(
        symbol="BTC/USD",
        direction=SignalDirection.BUY,
        strength=0.8,
        confidence=0.9,
        timestamp=datetime.now(),
        strategy="scalping",
        metadata={"rsi": 30.0, "volume_spike": True}
    )