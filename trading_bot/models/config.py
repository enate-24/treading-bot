"""Configuration data models for the trading bot system."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum


class Environment(Enum):
    """Environment types for configuration."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class ExchangeConfig:
    """Configuration for exchange connection."""
    name: str
    api_key: str
    api_secret: str
    sandbox: bool = True
    rate_limit: int = 100
    timeout: int = 30
    priority: int = 1


@dataclass
class TradingConfig:
    """Main trading configuration."""
    symbols: List[str]
    timeframes: List[str]
    strategy: str
    risk_per_trade: float
    max_drawdown: float
    daily_loss_limit: float
    exchange_configs: Dict[str, ExchangeConfig] = field(default_factory=dict)


@dataclass
class ConfigurationVersion:
    """Configuration version for history tracking."""
    version: int
    config: Dict[str, Any]
    timestamp: datetime
    description: str
    environment: Environment


@dataclass
class ConfigurationConstraints:
    """Validation constraints for configuration parameters."""
    min_risk_per_trade: float = 0.001  # 0.1%
    max_risk_per_trade: float = 0.05   # 5%
    min_max_drawdown: float = 0.05     # 5%
    max_max_drawdown: float = 0.5      # 50%
    min_daily_loss_limit: float = 0.01 # 1%
    max_daily_loss_limit: float = 0.2  # 20%
    supported_timeframes: List[str] = field(default_factory=lambda: [
        "1m", "5m", "15m", "30m", "1h", "4h", "1d"
    ])
    supported_strategies: List[str] = field(default_factory=lambda: [
        "scalping", "swing_trading"
    ])
    max_symbols: int = 50
    min_rate_limit: int = 1
    max_rate_limit: int = 1000
    min_timeout: int = 5
    max_timeout: int = 300