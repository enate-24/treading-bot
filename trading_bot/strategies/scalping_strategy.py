"""Scalping trading strategy implementation."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from ..interfaces.signal_generator import ITradingStrategy
from ..models import MarketData, TradingSignal, SignalDirection


logger = logging.getLogger(__name__)


class ScalpingStrategy(ITradingStrategy):
    """Scalping strategy using RSI and volume-based signals.
    
    This strategy focuses on short-term price movements with:
    - RSI oversold/overbought conditions
    - Volume spike detection
    - Quick profit targets (0.1-0.5%)
    - Tight stop losses
    - 1-5 minute timeframes
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        """Initialize scalping strategy.
        
        Args:
            parameters: Strategy parameters including:
                - rsi_oversold: RSI level for oversold condition (default: 30)
                - rsi_overbought: RSI level for overbought condition (default: 70)
                - volume_threshold: Volume spike multiplier (default: 1.5)
                - profit_target: Profit target percentage (default: 0.003, i.e., 0.3%)
                - stop_loss: Stop loss percentage (default: 0.002, i.e., 0.2%)
                - min_confidence: Minimum confidence for signal generation (default: 0.6)
                - lookback_periods: Number of periods for volume average (default: 20)
        """
        default_params = {
            'rsi_oversold': 30.0,
            'rsi_overbought': 70.0,
            'volume_threshold': 1.5,
            'profit_target': 0.003,  # 0.3%
            'stop_loss': 0.002,      # 0.2%
            'min_confidence': 0.6,
            'lookback_periods': 20
        }
        
        # Merge default parameters with provided ones
        self.parameters = {**default_params, **(parameters or {})}
        self.name = "ScalpingStrategy"
        
        # Initialize strategy state
        self._state = {
            'last_signal_time': None,
            'volume_history': [],
            'price_history': [],
            'signal_count': 0,
            'last_rsi': None,
            'last_volume': None,
            'avg_volume': None
        }
    
    def get_name(self) -> str:
        """Get strategy name."""
        return self.name
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return self.parameters.copy()
    
    def analyze(self, market_data: MarketData) -> Optional[TradingSignal]:
        """Analyze market data and generate scalping signals.
        
        Args:
            market_data: Current market data with indicators
            
        Returns:
            Trading signal or None if no signal generated
        """
        try:
            # Extract required indicators
            rsi = market_data.indicators.get('RSI')
            current_volume = float(market_data.ohlcv.volume)
            current_price = float(market_data.ohlcv.close)
            
            if rsi is None:
                logger.warning(f"RSI indicator missing for {market_data.symbol}")
                return None
            
            # Update state with current data
            self._update_state(market_data, rsi, current_volume, current_price)
            
            # Calculate volume spike (use default if insufficient data)
            volume_spike = self._calculate_volume_spike(current_volume)
            
            # Check if we have enough data for full analysis
            if not self._has_sufficient_data():
                # Generate simple RSI-based signal as fallback when insufficient volume data
                # This ensures the strategy can still operate with limited data
                if rsi <= self.parameters['rsi_oversold']:
                    strength = max(0.0, (self.parameters['rsi_oversold'] - rsi) / self.parameters['rsi_oversold'])
                    confidence = min(0.8, strength + 0.2)  # Base confidence
                    
                    if confidence >= self.parameters['min_confidence']:
                        return TradingSignal(
                            symbol=market_data.symbol,
                            direction=SignalDirection.BUY,
                            strength=strength,
                            confidence=confidence,
                            timestamp=market_data.timestamp,
                            strategy=self.name,
                            metadata={
                                'rsi': rsi,
                                'volume_spike': volume_spike,  # Always include volume_spike
                                'avg_volume': self._state.get('avg_volume', 0.0),
                                'current_volume': current_volume,
                                'profit_target': self.parameters['profit_target'],
                                'stop_loss': self.parameters['stop_loss'],
                                'entry_price': float(market_data.ohlcv.close),
                                'fallback_mode': True  # Indicate this is a fallback signal
                            }
                        )
                elif rsi >= self.parameters['rsi_overbought']:
                    strength = max(0.0, (rsi - self.parameters['rsi_overbought']) / (100 - self.parameters['rsi_overbought']))
                    confidence = min(0.8, strength + 0.2)  # Base confidence
                    
                    if confidence >= self.parameters['min_confidence']:
                        return TradingSignal(
                            symbol=market_data.symbol,
                            direction=SignalDirection.SELL,
                            strength=strength,
                            confidence=confidence,
                            timestamp=market_data.timestamp,
                            strategy=self.name,
                            metadata={
                                'rsi': rsi,
                                'volume_spike': volume_spike,  # Always include volume_spike
                                'avg_volume': self._state.get('avg_volume', 0.0),
                                'current_volume': current_volume,
                                'profit_target': self.parameters['profit_target'],
                                'stop_loss': self.parameters['stop_loss'],
                                'entry_price': float(market_data.ohlcv.close),
                                'fallback_mode': True  # Indicate this is a fallback signal
                            }
                        )
                return None
            
            # Generate signal based on RSI and volume conditions
            signal = self._generate_signal(market_data, rsi, volume_spike)
            
            if signal:
                self._state['signal_count'] += 1
                self._state['last_signal_time'] = market_data.timestamp
                logger.info(f"Generated scalping signal: {signal.direction.value} for {signal.symbol}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error in scalping strategy analysis for {market_data.symbol}: {e}")
            return None
    
    def _update_state(self, market_data: MarketData, rsi: float, volume: float, price: float) -> None:
        """Update strategy state with current market data.
        
        Args:
            market_data: Current market data
            rsi: Current RSI value
            volume: Current volume
            price: Current price
        """
        try:
            # Update volume history
            self._state['volume_history'].append(volume)
            if len(self._state['volume_history']) > self.parameters['lookback_periods']:
                self._state['volume_history'].pop(0)
            
            # Update price history
            self._state['price_history'].append(price)
            if len(self._state['price_history']) > self.parameters['lookback_periods']:
                self._state['price_history'].pop(0)
            
            # Update current values
            self._state['last_rsi'] = rsi
            self._state['last_volume'] = volume
            
            # Calculate average volume
            if len(self._state['volume_history']) >= 5:  # Need at least 5 periods
                self._state['avg_volume'] = sum(self._state['volume_history']) / len(self._state['volume_history'])
        except Exception as e:
            logger.error(f"Error updating strategy state: {e}")
            # Continue execution even if state update fails
    
    def _has_sufficient_data(self) -> bool:
        """Check if we have sufficient data for analysis.
        
        Returns:
            True if sufficient data available
        """
        return (len(self._state['volume_history']) >= 5 and 
                self._state['avg_volume'] is not None and
                self._state['last_rsi'] is not None)
    
    def _calculate_volume_spike(self, current_volume: float) -> float:
        """Calculate volume spike ratio.
        
        Args:
            current_volume: Current volume
            
        Returns:
            Volume spike ratio (current_volume / average_volume)
        """
        if self._state['avg_volume'] is None or self._state['avg_volume'] == 0:
            return 1.0
        
        return current_volume / self._state['avg_volume']
    
    def _generate_signal(self, market_data: MarketData, rsi: float, volume_spike: float) -> Optional[TradingSignal]:
        """Generate trading signal based on RSI and volume conditions.
        
        Args:
            market_data: Current market data
            rsi: Current RSI value
            volume_spike: Volume spike ratio
            
        Returns:
            Trading signal or None
        """
        # Check for signal cooldown (prevent too frequent signals)
        if self._state['last_signal_time']:
            time_since_last = market_data.timestamp - self._state['last_signal_time']
            if time_since_last < timedelta(minutes=1):  # 1-minute cooldown
                return None
        
        # Check RSI conditions
        rsi_oversold = rsi <= self.parameters['rsi_oversold']
        rsi_overbought = rsi >= self.parameters['rsi_overbought']
        
        # Check volume spike condition
        volume_condition = volume_spike >= self.parameters['volume_threshold']
        
        # Generate buy signal (RSI oversold + volume spike)
        if rsi_oversold and volume_condition:
            strength = self._calculate_signal_strength(rsi, volume_spike, is_buy=True)
            confidence = self._calculate_confidence(rsi, volume_spike, is_buy=True)
            
            if confidence >= self.parameters['min_confidence']:
                # Ensure all metadata fields are present
                metadata = {
                    'rsi': rsi,
                    'volume_spike': volume_spike,
                    'avg_volume': self._state.get('avg_volume', 0.0),
                    'current_volume': self._state.get('last_volume', 0.0),
                    'profit_target': self.parameters['profit_target'],
                    'stop_loss': self.parameters['stop_loss'],
                    'entry_price': float(market_data.ohlcv.close)
                }
                
                return TradingSignal(
                    symbol=market_data.symbol,
                    direction=SignalDirection.BUY,
                    strength=strength,
                    confidence=confidence,
                    timestamp=market_data.timestamp,
                    strategy=self.name,
                    metadata=metadata
                )
        
        # Generate sell signal (RSI overbought + volume spike)
        elif rsi_overbought and volume_condition:
            strength = self._calculate_signal_strength(rsi, volume_spike, is_buy=False)
            confidence = self._calculate_confidence(rsi, volume_spike, is_buy=False)
            
            if confidence >= self.parameters['min_confidence']:
                # Ensure all metadata fields are present
                metadata = {
                    'rsi': rsi,
                    'volume_spike': volume_spike,
                    'avg_volume': self._state.get('avg_volume', 0.0),
                    'current_volume': self._state.get('last_volume', 0.0),
                    'profit_target': self.parameters['profit_target'],
                    'stop_loss': self.parameters['stop_loss'],
                    'entry_price': float(market_data.ohlcv.close)
                }
                
                return TradingSignal(
                    symbol=market_data.symbol,
                    direction=SignalDirection.SELL,
                    strength=strength,
                    confidence=confidence,
                    timestamp=market_data.timestamp,
                    strategy=self.name,
                    metadata=metadata
                )
        
        return None
    
    def _calculate_signal_strength(self, rsi: float, volume_spike: float, is_buy: bool) -> float:
        """Calculate signal strength based on RSI and volume conditions.
        
        Args:
            rsi: Current RSI value
            volume_spike: Volume spike ratio
            is_buy: True for buy signal, False for sell signal
            
        Returns:
            Signal strength between 0.0 and 1.0
        """
        if is_buy:
            # For buy signals, stronger when RSI is more oversold
            rsi_strength = max(0.0, (self.parameters['rsi_oversold'] - rsi) / self.parameters['rsi_oversold'])
        else:
            # For sell signals, stronger when RSI is more overbought
            rsi_strength = max(0.0, (rsi - self.parameters['rsi_overbought']) / (100 - self.parameters['rsi_overbought']))
        
        # Volume strength based on spike magnitude
        volume_strength = min(1.0, (volume_spike - 1.0) / 2.0)  # Normalize to 0-1
        
        # Combine RSI and volume strength
        combined_strength = (rsi_strength * 0.6) + (volume_strength * 0.4)
        
        return min(1.0, max(0.0, combined_strength))
    
    def _calculate_confidence(self, rsi: float, volume_spike: float, is_buy: bool) -> float:
        """Calculate signal confidence based on market conditions.
        
        Args:
            rsi: Current RSI value
            volume_spike: Volume spike ratio
            is_buy: True for buy signal, False for sell signal
            
        Returns:
            Signal confidence between 0.0 and 1.0
        """
        # Base confidence from RSI extremes
        if is_buy:
            rsi_confidence = max(0.0, (self.parameters['rsi_oversold'] - rsi) / 20.0)  # More confident when more oversold
        else:
            rsi_confidence = max(0.0, (rsi - self.parameters['rsi_overbought']) / 20.0)  # More confident when more overbought
        
        # Volume confidence
        volume_confidence = min(1.0, volume_spike / 3.0)  # Higher volume = higher confidence
        
        # Price momentum confidence (using recent price history)
        momentum_confidence = self._calculate_momentum_confidence(is_buy)
        
        # Combine all confidence factors
        total_confidence = (rsi_confidence * 0.4) + (volume_confidence * 0.4) + (momentum_confidence * 0.2)
        
        return min(1.0, max(0.0, total_confidence))
    
    def _calculate_momentum_confidence(self, is_buy: bool) -> float:
        """Calculate confidence based on recent price momentum.
        
        Args:
            is_buy: True for buy signal, False for sell signal
            
        Returns:
            Momentum confidence between 0.0 and 1.0
        """
        if len(self._state['price_history']) < 3:
            return 0.5  # Neutral confidence if insufficient data
        
        # Calculate short-term momentum (last 3 periods)
        recent_prices = self._state['price_history'][-3:]
        price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
        
        if is_buy:
            # For buy signals, prefer recent downward momentum (potential reversal)
            return max(0.0, min(1.0, -price_change * 10 + 0.5))
        else:
            # For sell signals, prefer recent upward momentum (potential reversal)
            return max(0.0, min(1.0, price_change * 10 + 0.5))
    
    def reset_state(self) -> None:
        """Reset strategy state."""
        self._state = {
            'last_signal_time': None,
            'volume_history': [],
            'price_history': [],
            'signal_count': 0,
            'last_rsi': None,
            'last_volume': None,
            'avg_volume': None
        }