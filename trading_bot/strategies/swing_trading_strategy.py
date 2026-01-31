"""Swing trading strategy implementation."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from ..interfaces.signal_generator import ITradingStrategy
from ..models import MarketData, TradingSignal, SignalDirection


logger = logging.getLogger(__name__)


class SwingTradingStrategy(ITradingStrategy):
    """Swing trading strategy using moving average crossovers and trend confirmation.
    
    This strategy focuses on medium-term trends with:
    - Moving average crossover signals (SMA_20 and SMA_50)
    - Trend confirmation using price action
    - Medium-term profit targets (2-5%)
    - Wider stop losses for trend following
    - 1-4 hour timeframes
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        """Initialize swing trading strategy.
        
        Args:
            parameters: Strategy parameters including:
                - fast_ma_period: Fast moving average period (default: 20)
                - slow_ma_period: Slow moving average period (default: 50)
                - trend_confirmation_periods: Periods for trend confirmation (default: 5)
                - profit_target: Profit target percentage (default: 0.03, i.e., 3%)
                - stop_loss: Stop loss percentage (default: 0.015, i.e., 1.5%)
                - min_confidence: Minimum confidence for signal generation (default: 0.7)
                - crossover_threshold: Minimum percentage difference for crossover (default: 0.001, i.e., 0.1%)
                - volume_confirmation: Require volume confirmation (default: True)
                - volume_threshold: Volume multiplier for confirmation (default: 1.2)
        """
        default_params = {
            'fast_ma_period': 20,
            'slow_ma_period': 50,
            'trend_confirmation_periods': 5,
            'profit_target': 0.03,      # 3%
            'stop_loss': 0.015,         # 1.5%
            'min_confidence': 0.7,
            'crossover_threshold': 0.001,  # 0.1%
            'volume_confirmation': True,
            'volume_threshold': 1.2
        }
        
        # Merge default parameters with provided ones
        self.parameters = {**default_params, **(parameters or {})}
        self.name = "SwingTradingStrategy"
        
        # Initialize strategy state
        self._state = {
            'last_signal_time': None,
            'last_crossover_time': None,
            'current_trend': None,  # 'BULLISH', 'BEARISH', or None
            'crossover_direction': None,  # 'GOLDEN' (bullish) or 'DEATH' (bearish)
            'fast_ma_history': [],
            'slow_ma_history': [],
            'price_history': [],
            'volume_history': [],
            'signal_count': 0,
            'trend_strength': 0.0,
            'last_fast_ma': None,
            'last_slow_ma': None,
            'avg_volume': None
        }
    
    def get_name(self) -> str:
        """Get strategy name."""
        return self.name
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return self.parameters.copy()
    
    def analyze(self, market_data: MarketData) -> Optional[TradingSignal]:
        """Analyze market data and generate swing trading signals.
        
        Args:
            market_data: Current market data with indicators
            
        Returns:
            Trading signal or None if no signal generated
        """
        try:
            # Extract required indicators
            fast_ma = market_data.indicators.get(f'SMA_{self.parameters["fast_ma_period"]}')
            slow_ma = market_data.indicators.get(f'SMA_{self.parameters["slow_ma_period"]}')
            current_price = float(market_data.ohlcv.close)
            current_volume = float(market_data.ohlcv.volume)
            
            # Use fallback indicator names if specific periods not found
            if fast_ma is None:
                fast_ma = market_data.indicators.get('SMA_20')
            if slow_ma is None:
                slow_ma = market_data.indicators.get('SMA_50')
            
            if fast_ma is None or slow_ma is None:
                logger.warning(f"Moving average indicators missing for {market_data.symbol}")
                return None
            
            # Update state with current data
            self._update_state(market_data, fast_ma, slow_ma, current_price, current_volume)
            
            # Check if we have enough data for analysis
            if not self._has_sufficient_data():
                return None
            
            # Detect crossover
            crossover_signal = self._detect_crossover()
            
            if crossover_signal:
                # Confirm trend and generate signal
                signal = self._generate_signal(market_data, crossover_signal)
                
                if signal:
                    self._state['signal_count'] += 1
                    self._state['last_signal_time'] = market_data.timestamp
                    logger.info(f"Generated swing trading signal: {signal.direction.value} for {signal.symbol}")
                
                return signal
            
            return None
            
        except Exception as e:
            logger.error(f"Error in swing trading strategy analysis for {market_data.symbol}: {e}")
            return None
    
    def _update_state(self, market_data: MarketData, fast_ma: float, slow_ma: float, 
                     price: float, volume: float) -> None:
        """Update strategy state with current market data.
        
        Args:
            market_data: Current market data
            fast_ma: Fast moving average value
            slow_ma: Slow moving average value
            price: Current price
            volume: Current volume
        """
        # Update moving average history
        self._state['fast_ma_history'].append(fast_ma)
        if len(self._state['fast_ma_history']) > self.parameters['trend_confirmation_periods'] + 1:
            self._state['fast_ma_history'].pop(0)
        
        self._state['slow_ma_history'].append(slow_ma)
        if len(self._state['slow_ma_history']) > self.parameters['trend_confirmation_periods'] + 1:
            self._state['slow_ma_history'].pop(0)
        
        # Update price and volume history
        self._state['price_history'].append(price)
        if len(self._state['price_history']) > self.parameters['trend_confirmation_periods'] + 1:
            self._state['price_history'].pop(0)
        
        self._state['volume_history'].append(volume)
        if len(self._state['volume_history']) > 20:  # Keep 20 periods for volume average
            self._state['volume_history'].pop(0)
        
        # Update current values
        self._state['last_fast_ma'] = fast_ma
        self._state['last_slow_ma'] = slow_ma
        
        # Calculate average volume
        if len(self._state['volume_history']) >= 10:
            self._state['avg_volume'] = sum(self._state['volume_history']) / len(self._state['volume_history'])
        
        # Update trend analysis
        self._update_trend_analysis()
    
    def _has_sufficient_data(self) -> bool:
        """Check if we have sufficient data for analysis.
        
        Returns:
            True if sufficient data available
        """
        return (len(self._state['fast_ma_history']) >= 2 and 
                len(self._state['slow_ma_history']) >= 2 and
                self._state['last_fast_ma'] is not None and
                self._state['last_slow_ma'] is not None)
    
    def _update_trend_analysis(self) -> None:
        """Update current trend analysis."""
        if len(self._state['fast_ma_history']) < self.parameters['trend_confirmation_periods']:
            return
        
        # Analyze trend strength based on MA separation and direction
        fast_ma = self._state['last_fast_ma']
        slow_ma = self._state['last_slow_ma']
        
        # Calculate trend strength based on MA separation
        ma_separation = abs(fast_ma - slow_ma) / slow_ma
        self._state['trend_strength'] = min(1.0, ma_separation * 20)  # Normalize to 0-1
        
        # Determine current trend
        if fast_ma > slow_ma:
            self._state['current_trend'] = 'BULLISH'
        elif fast_ma < slow_ma:
            self._state['current_trend'] = 'BEARISH'
        else:
            self._state['current_trend'] = None
    
    def _detect_crossover(self) -> Optional[str]:
        """Detect moving average crossover.
        
        Returns:
            'GOLDEN' for bullish crossover, 'DEATH' for bearish crossover, or None
        """
        if len(self._state['fast_ma_history']) < 2 or len(self._state['slow_ma_history']) < 2:
            return None
        
        # Current and previous MA values
        fast_current = self._state['fast_ma_history'][-1]
        fast_previous = self._state['fast_ma_history'][-2]
        slow_current = self._state['slow_ma_history'][-1]
        slow_previous = self._state['slow_ma_history'][-2]
        
        # Check for golden cross (bullish crossover)
        if (fast_previous <= slow_previous and fast_current > slow_current):
            # Verify crossover significance
            crossover_magnitude = (fast_current - slow_current) / slow_current
            if crossover_magnitude >= self.parameters['crossover_threshold']:
                self._state['crossover_direction'] = 'GOLDEN'
                return 'GOLDEN'
        
        # Check for death cross (bearish crossover)
        elif (fast_previous >= slow_previous and fast_current < slow_current):
            # Verify crossover significance
            crossover_magnitude = (slow_current - fast_current) / slow_current
            if crossover_magnitude >= self.parameters['crossover_threshold']:
                self._state['crossover_direction'] = 'DEATH'
                return 'DEATH'
        
        return None
    
    def _generate_signal(self, market_data: MarketData, crossover_type: str) -> Optional[TradingSignal]:
        """Generate trading signal based on crossover and confirmations.
        
        Args:
            market_data: Current market data
            crossover_type: 'GOLDEN' or 'DEATH'
            
        Returns:
            Trading signal or None
        """
        # Check for signal cooldown (prevent too frequent signals)
        if self._state['last_signal_time']:
            time_since_last = market_data.timestamp - self._state['last_signal_time']
            if time_since_last < timedelta(hours=2):  # 2-hour cooldown for swing trading
                return None
        
        # Volume confirmation if required
        if self.parameters['volume_confirmation']:
            if not self._check_volume_confirmation():
                return None
        
        # Trend confirmation
        if not self._check_trend_confirmation(crossover_type):
            return None
        
        # Generate signal based on crossover type
        if crossover_type == 'GOLDEN':
            strength = self._calculate_signal_strength(True)
            confidence = self._calculate_confidence(True)
            
            if confidence >= self.parameters['min_confidence']:
                return TradingSignal(
                    symbol=market_data.symbol,
                    direction=SignalDirection.BUY,
                    strength=strength,
                    confidence=confidence,
                    timestamp=market_data.timestamp,
                    strategy=self.name,
                    metadata={
                        'crossover_type': 'GOLDEN',
                        'fast_ma': self._state['last_fast_ma'],
                        'slow_ma': self._state['last_slow_ma'],
                        'trend_strength': self._state['trend_strength'],
                        'profit_target': self.parameters['profit_target'],
                        'stop_loss': self.parameters['stop_loss'],
                        'entry_price': float(market_data.ohlcv.close)
                    }
                )
        
        elif crossover_type == 'DEATH':
            strength = self._calculate_signal_strength(False)
            confidence = self._calculate_confidence(False)
            
            if confidence >= self.parameters['min_confidence']:
                return TradingSignal(
                    symbol=market_data.symbol,
                    direction=SignalDirection.SELL,
                    strength=strength,
                    confidence=confidence,
                    timestamp=market_data.timestamp,
                    strategy=self.name,
                    metadata={
                        'crossover_type': 'DEATH',
                        'fast_ma': self._state['last_fast_ma'],
                        'slow_ma': self._state['last_slow_ma'],
                        'trend_strength': self._state['trend_strength'],
                        'profit_target': self.parameters['profit_target'],
                        'stop_loss': self.parameters['stop_loss'],
                        'entry_price': float(market_data.ohlcv.close)
                    }
                )
        
        return None
    
    def _check_volume_confirmation(self) -> bool:
        """Check if volume confirms the signal.
        
        Returns:
            True if volume confirmation is satisfied
        """
        if self._state['avg_volume'] is None or len(self._state['volume_history']) == 0:
            return True  # Skip volume check if no data
        
        current_volume = self._state['volume_history'][-1]
        return current_volume >= (self._state['avg_volume'] * self.parameters['volume_threshold'])
    
    def _check_trend_confirmation(self, crossover_type: str) -> bool:
        """Check if trend confirms the crossover signal.
        
        Args:
            crossover_type: 'GOLDEN' or 'DEATH'
            
        Returns:
            True if trend confirmation is satisfied
        """
        if len(self._state['price_history']) < self.parameters['trend_confirmation_periods']:
            return True  # Skip trend check if insufficient data
        
        # Check price momentum in the direction of the crossover
        recent_prices = self._state['price_history'][-self.parameters['trend_confirmation_periods']:]
        price_momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
        
        if crossover_type == 'GOLDEN':
            # For bullish crossover, prefer recent upward momentum or sideways
            return price_momentum >= -0.02  # Allow up to 2% recent decline
        else:  # DEATH crossover
            # For bearish crossover, prefer recent downward momentum or sideways
            return price_momentum <= 0.02   # Allow up to 2% recent gain
    
    def _calculate_signal_strength(self, is_buy: bool) -> float:
        """Calculate signal strength based on trend and crossover conditions.
        
        Args:
            is_buy: True for buy signal, False for sell signal
            
        Returns:
            Signal strength between 0.0 and 1.0
        """
        # Base strength from trend strength
        trend_strength = self._state['trend_strength']
        
        # MA separation strength
        fast_ma = self._state['last_fast_ma']
        slow_ma = self._state['last_slow_ma']
        ma_separation = abs(fast_ma - slow_ma) / slow_ma
        separation_strength = min(1.0, ma_separation * 10)
        
        # Volume strength
        volume_strength = 0.5  # Default neutral
        if self._state['avg_volume'] and len(self._state['volume_history']) > 0:
            current_volume = self._state['volume_history'][-1]
            volume_ratio = current_volume / self._state['avg_volume']
            volume_strength = min(1.0, volume_ratio / 2.0)
        
        # Combine all strength factors
        combined_strength = (trend_strength * 0.4) + (separation_strength * 0.4) + (volume_strength * 0.2)
        
        return min(1.0, max(0.0, combined_strength))
    
    def _calculate_confidence(self, is_buy: bool) -> float:
        """Calculate signal confidence based on multiple confirmations.
        
        Args:
            is_buy: True for buy signal, False for sell signal
            
        Returns:
            Signal confidence between 0.0 and 1.0
        """
        # Trend alignment confidence
        trend_confidence = 0.5  # Default neutral
        if self._state['current_trend']:
            if (is_buy and self._state['current_trend'] == 'BULLISH') or \
               (not is_buy and self._state['current_trend'] == 'BEARISH'):
                trend_confidence = 0.8
            else:
                trend_confidence = 0.3  # Counter-trend signal
        
        # MA separation confidence (wider separation = higher confidence)
        fast_ma = self._state['last_fast_ma']
        slow_ma = self._state['last_slow_ma']
        separation_confidence = min(1.0, abs(fast_ma - slow_ma) / slow_ma * 15)
        
        # Volume confirmation confidence
        volume_confidence = 0.5  # Default neutral
        if self.parameters['volume_confirmation'] and self._check_volume_confirmation():
            volume_confidence = 0.8
        elif self.parameters['volume_confirmation']:
            volume_confidence = 0.3
        
        # Price momentum confidence
        momentum_confidence = self._calculate_momentum_confidence(is_buy)
        
        # Combine all confidence factors
        total_confidence = (trend_confidence * 0.3) + (separation_confidence * 0.3) + \
                          (volume_confidence * 0.2) + (momentum_confidence * 0.2)
        
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
        
        # Calculate momentum over different timeframes
        short_momentum = (self._state['price_history'][-1] - self._state['price_history'][-2]) / self._state['price_history'][-2]
        
        if len(self._state['price_history']) >= 5:
            medium_momentum = (self._state['price_history'][-1] - self._state['price_history'][-5]) / self._state['price_history'][-5]
        else:
            medium_momentum = short_momentum
        
        if is_buy:
            # For buy signals, prefer positive momentum
            short_conf = max(0.0, min(1.0, short_momentum * 20 + 0.5))
            medium_conf = max(0.0, min(1.0, medium_momentum * 10 + 0.5))
        else:
            # For sell signals, prefer negative momentum
            short_conf = max(0.0, min(1.0, -short_momentum * 20 + 0.5))
            medium_conf = max(0.0, min(1.0, -medium_momentum * 10 + 0.5))
        
        return (short_conf * 0.6) + (medium_conf * 0.4)
    
    def reset_state(self) -> None:
        """Reset strategy state."""
        self._state = {
            'last_signal_time': None,
            'last_crossover_time': None,
            'current_trend': None,
            'crossover_direction': None,
            'fast_ma_history': [],
            'slow_ma_history': [],
            'price_history': [],
            'volume_history': [],
            'signal_count': 0,
            'trend_strength': 0.0,
            'last_fast_ma': None,
            'last_slow_ma': None,
            'avg_volume': None
        }