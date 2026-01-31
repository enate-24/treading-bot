"""Signal Generator implementation for trading strategies."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import pandas as pd

from .interfaces.signal_generator import ISignalGenerator, ITradingStrategy
from .models import MarketData, TradingSignal


logger = logging.getLogger(__name__)


class TradingStrategy(ITradingStrategy):
    """Abstract base class for trading strategies."""
    
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        """Initialize trading strategy.
        
        Args:
            name: Strategy name
            parameters: Strategy parameters dictionary
        """
        self.name = name
        self.parameters = parameters or {}
        self._state: Dict[str, Any] = {}
    
    def get_name(self) -> str:
        """Get strategy name."""
        return self.name
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return self.parameters.copy()
    
    def get_state(self) -> Dict[str, Any]:
        """Get current strategy state."""
        return self._state.copy()
    
    def update_state(self, key: str, value: Any) -> None:
        """Update strategy state.
        
        Args:
            key: State key
            value: State value
        """
        self._state[key] = value


class SignalGenerator(ISignalGenerator):
    """Concrete implementation of signal generator."""
    
    def __init__(self):
        """Initialize signal generator."""
        self._strategy: Optional[ITradingStrategy] = None
        self._strategy_states: Dict[str, Dict[str, Any]] = {}
        self._last_signals: Dict[str, TradingSignal] = {}
    
    def analyze_market_data(self, data: MarketData) -> Optional[TradingSignal]:
        """Analyze market data and generate trading signals.
        
        Args:
            data: Market data with technical indicators
            
        Returns:
            Trading signal or None if no signal generated
        """
        if not self._strategy:
            logger.warning("No strategy set for signal generation")
            return None
        
        try:
            # Generate signal using current strategy
            signal = self._strategy.analyze(data)
            
            if signal:
                # Store the signal for tracking
                self._last_signals[data.symbol] = signal
                
                # Update strategy state for this symbol
                if hasattr(self._strategy, 'get_state'):
                    self._strategy_states[data.symbol] = self._strategy.get_state()
                
                logger.info(f"Generated {signal.direction.value} signal for {signal.symbol} "
                           f"with strength {signal.strength:.2f} and confidence {signal.confidence:.2f}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error analyzing market data for {data.symbol}: {e}")
            return None
    
    def set_strategy(self, strategy: ITradingStrategy) -> None:
        """Set the active trading strategy.
        
        Args:
            strategy: Trading strategy to use
        """
        self._strategy = strategy
        logger.info(f"Set active strategy to: {strategy.get_name()}")
    
    def get_strategy_state(self, symbol: str) -> Dict[str, Any]:
        """Get current strategy state for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary containing strategy state
        """
        return self._strategy_states.get(symbol, {})
    
    def backtest_strategy(self, historical_data: pd.DataFrame) -> Dict[str, Any]:
        """Backtest strategy on historical data.
        
        Args:
            historical_data: Historical market data DataFrame with OHLCV columns
            
        Returns:
            Backtest results dictionary
        """
        if not self._strategy:
            raise ValueError("No strategy set for backtesting")
        
        if historical_data.empty:
            return {
                'total_signals': 0,
                'buy_signals': 0,
                'sell_signals': 0,
                'error': 'No historical data provided'
            }
        
        try:
            signals = []
            buy_signals = 0
            sell_signals = 0
            
            # Process each row of historical data
            for timestamp, row in historical_data.iterrows():
                # Create MarketData object from historical row
                from .models import OHLCV
                from decimal import Decimal
                
                ohlcv = OHLCV(
                    open=Decimal(str(row['open'])),
                    high=Decimal(str(row['high'])),
                    low=Decimal(str(row['low'])),
                    close=Decimal(str(row['close'])),
                    volume=Decimal(str(row['volume']))
                )
                
                # Create basic indicators if not present
                indicators = {}
                if 'RSI' in row:
                    indicators['RSI'] = float(row['RSI'])
                if 'SMA_20' in row:
                    indicators['SMA_20'] = float(row['SMA_20'])
                if 'SMA_50' in row:
                    indicators['SMA_50'] = float(row['SMA_50'])
                
                market_data = MarketData(
                    symbol='BACKTEST',
                    timestamp=timestamp if isinstance(timestamp, datetime) else datetime.now(),
                    ohlcv=ohlcv,
                    indicators=indicators
                )
                
                # Generate signal
                signal = self._strategy.analyze(market_data)
                if signal:
                    signals.append(signal)
                    if signal.direction.value == 'BUY':
                        buy_signals += 1
                    else:
                        sell_signals += 1
            
            return {
                'total_signals': len(signals),
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'signals': signals,
                'strategy_name': self._strategy.get_name(),
                'strategy_parameters': self._strategy.get_parameters()
            }
            
        except Exception as e:
            logger.error(f"Error during backtesting: {e}")
            return {
                'total_signals': 0,
                'buy_signals': 0,
                'sell_signals': 0,
                'error': str(e)
            }
    
    def get_last_signal(self, symbol: str) -> Optional[TradingSignal]:
        """Get the last generated signal for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Last trading signal or None
        """
        return self._last_signals.get(symbol)
    
    def clear_signals(self, symbol: str = None) -> None:
        """Clear stored signals.
        
        Args:
            symbol: Specific symbol to clear, or None to clear all
        """
        if symbol:
            self._last_signals.pop(symbol, None)
            self._strategy_states.pop(symbol, None)
        else:
            self._last_signals.clear()
            self._strategy_states.clear()