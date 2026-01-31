"""Unit tests for interface definitions."""

import pytest
from abc import ABC
from trading_bot.interfaces import (
    IDataHandler, ISignalGenerator, ITradingStrategy, IPortfolioManager,
    IRiskManager, IExecutionEngine, IPerformanceMonitor,
    IConfigurationManager, IComplianceSystem
)


class TestInterfaces:
    """Test interface definitions."""
    
    def test_interfaces_are_abstract(self):
        """Test that all interfaces are abstract base classes."""
        interfaces = [
            IDataHandler, ISignalGenerator, ITradingStrategy, IPortfolioManager,
            IRiskManager, IExecutionEngine, IPerformanceMonitor,
            IConfigurationManager, IComplianceSystem
        ]
        
        for interface in interfaces:
            assert issubclass(interface, ABC)
            # Verify we cannot instantiate abstract interfaces
            with pytest.raises(TypeError):
                interface()
    
    def test_data_handler_interface_methods(self):
        """Test DataHandler interface has required methods."""
        required_methods = [
            'subscribe_to_symbol', 'get_latest_price', 'get_indicator_value',
            'get_historical_data', 'register_data_callback'
        ]
        
        for method in required_methods:
            assert hasattr(IDataHandler, method)
            assert callable(getattr(IDataHandler, method))
    
    def test_signal_generator_interface_methods(self):
        """Test SignalGenerator interface has required methods."""
        required_methods = [
            'analyze_market_data', 'set_strategy', 'get_strategy_state',
            'backtest_strategy'
        ]
        
        for method in required_methods:
            assert hasattr(ISignalGenerator, method)
            assert callable(getattr(ISignalGenerator, method))
    
    def test_trading_strategy_interface_methods(self):
        """Test TradingStrategy interface has required methods."""
        required_methods = ['analyze', 'get_name', 'get_parameters']
        
        for method in required_methods:
            assert hasattr(ITradingStrategy, method)
            assert callable(getattr(ITradingStrategy, method))
    
    def test_portfolio_manager_interface_methods(self):
        """Test PortfolioManager interface has required methods."""
        required_methods = [
            'calculate_position_size', 'get_current_positions',
            'get_available_capital', 'update_position', 'get_portfolio_metrics'
        ]
        
        for method in required_methods:
            assert hasattr(IPortfolioManager, method)
            assert callable(getattr(IPortfolioManager, method))
    
    def test_risk_manager_interface_methods(self):
        """Test RiskManager interface has required methods."""
        required_methods = [
            'validate_trade', 'monitor_positions', 'trigger_emergency_stop',
            'update_stop_loss', 'get_risk_metrics'
        ]
        
        for method in required_methods:
            assert hasattr(IRiskManager, method)
            assert callable(getattr(IRiskManager, method))
    
    def test_execution_engine_interface_methods(self):
        """Test ExecutionEngine interface has required methods."""
        required_methods = [
            'place_order', 'cancel_order', 'get_order_status',
            'get_execution_history', 'get_open_orders'
        ]
        
        for method in required_methods:
            assert hasattr(IExecutionEngine, method)
            assert callable(getattr(IExecutionEngine, method))
    
    def test_performance_monitor_interface_methods(self):
        """Test PerformanceMonitor interface has required methods."""
        required_methods = [
            'calculate_sharpe_ratio', 'calculate_max_drawdown',
            'generate_performance_report', 'update_trade_metrics',
            'get_real_time_metrics'
        ]
        
        for method in required_methods:
            assert hasattr(IPerformanceMonitor, method)
            assert callable(getattr(IPerformanceMonitor, method))