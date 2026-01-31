"""
Trading Bot System - Automated Trading Platform

A comprehensive Python-based algorithmic trading platform designed for 
automated trading across multiple exchanges with configurable strategies,
robust risk management, and real-time monitoring.
"""

from .data_handler import DataHandler
from .signal_generator import SignalGenerator
from .portfolio_manager import PortfolioManager
from .risk_manager import RiskManager
from .performance_monitor import PerformanceMonitor
from .configuration_manager import ConfigurationManager

__version__ = "1.0.0"
__author__ = "Trading Bot Team"

__all__ = [
    "DataHandler",
    "SignalGenerator", 
    "PortfolioManager",
    "RiskManager",
    "PerformanceMonitor",
    "ConfigurationManager"
]