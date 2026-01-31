"""Base interfaces for trading bot components."""

from .data_handler import IDataHandler
from .signal_generator import ISignalGenerator, ITradingStrategy
from .portfolio_manager import IPortfolioManager
from .risk_manager import IRiskManager
from .execution_engine import IExecutionEngine
from .performance_monitor import IPerformanceMonitor
from .configuration_manager import IConfigurationManager
from .compliance_system import IComplianceSystem

__all__ = [
    "IDataHandler",
    "ISignalGenerator",
    "ITradingStrategy",
    "IPortfolioManager",
    "IRiskManager",
    "IExecutionEngine",
    "IPerformanceMonitor",
    "IConfigurationManager",
    "IComplianceSystem"
]