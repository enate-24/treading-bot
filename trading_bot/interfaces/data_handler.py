"""Data Handler interface for market data processing."""

from abc import ABC, abstractmethod
from typing import Callable, Optional
from pandas import DataFrame
from ..models import Price, MarketData


class IDataHandler(ABC):
    """Interface for handling market data ingestion and processing."""

    @abstractmethod
    def subscribe_to_symbol(self, symbol: str, timeframe: str) -> None:
        """Subscribe to real-time data for a trading symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USD')
            timeframe: Data timeframe (e.g., '1m', '5m', '1h')
        """
        pass

    @abstractmethod
    def get_latest_price(self, symbol: str) -> Optional[Price]:
        """Get the latest price data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Latest price data or None if not available
        """
        pass

    @abstractmethod
    def get_indicator_value(self, symbol: str, indicator: str) -> Optional[float]:
        """Get the latest value of a technical indicator.
        
        Args:
            symbol: Trading symbol
            indicator: Indicator name (e.g., 'RSI', 'SMA_20')
            
        Returns:
            Indicator value or None if not available
        """
        pass

    @abstractmethod
    def get_historical_data(self, symbol: str, periods: int) -> DataFrame:
        """Get historical market data for backtesting.
        
        Args:
            symbol: Trading symbol
            periods: Number of periods to retrieve
            
        Returns:
            DataFrame with historical OHLCV data
        """
        pass

    @abstractmethod
    def register_data_callback(self, callback: Callable[[MarketData], None]) -> None:
        """Register callback for real-time market data updates.
        
        Args:
            callback: Function to call when new data arrives
        """
        pass