"""Signal Generator and Trading Strategy interfaces."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pandas import DataFrame
from ..models import MarketData, TradingSignal


class ITradingStrategy(ABC):
    """Interface for trading strategies."""

    @abstractmethod
    def analyze(self, market_data: MarketData) -> Optional[TradingSignal]:
        """Analyze market data and generate trading signal.
        
        Args:
            market_data: Current market data with indicators
            
        Returns:
            Trading signal or None if no signal generated
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get strategy name.
        
        Returns:
            Strategy name
        """
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters.
        
        Returns:
            Dictionary of strategy parameters
        """
        pass


class ISignalGenerator(ABC):
    """Interface for signal generation component."""

    @abstractmethod
    def analyze_market_data(self, data: MarketData) -> Optional[TradingSignal]:
        """Analyze market data and generate trading signals.
        
        Args:
            data: Market data with technical indicators
            
        Returns:
            Trading signal or None if no signal generated
        """
        pass

    @abstractmethod
    def set_strategy(self, strategy: ITradingStrategy) -> None:
        """Set the active trading strategy.
        
        Args:
            strategy: Trading strategy to use
        """
        pass

    @abstractmethod
    def get_strategy_state(self, symbol: str) -> Dict[str, Any]:
        """Get current strategy state for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary containing strategy state
        """
        pass

    @abstractmethod
    def backtest_strategy(self, historical_data: DataFrame) -> Dict[str, Any]:
        """Backtest strategy on historical data.
        
        Args:
            historical_data: Historical market data
            
        Returns:
            Backtest results dictionary
        """
        pass