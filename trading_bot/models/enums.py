"""Enumerations for trading bot system."""

from enum import Enum


class SignalDirection(Enum):
    """Trading signal direction."""
    BUY = "BUY"
    SELL = "SELL"


class OrderSide(Enum):
    """Order side for trading."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Order type for trading."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class TimeInForce(Enum):
    """Time in force for orders."""
    GTC = "GTC"  # Good Till Cancelled
    IOC = "IOC"  # Immediate Or Cancel
    FOK = "FOK"  # Fill Or Kill
    DAY = "DAY"  # Day order