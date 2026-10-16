"""High-Frequency Trading (HFT) strategy implementation."""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np

from ..interfaces.signal_generator import ITradingStrategy
from ..models import MarketData, TradingSignal, SignalDirection


logger = logging.getLogger(__name__)


class HFTStrategy(ITradingStrategy):
    """High-Frequency Trading strategy using micro-movements and order flow.
    
    This strategy focuses on:
    - Tick-by-tick price movements
    - Order book imbalances
    - Micro-trends (seconds to minutes)
    - Statistical arbitrage
    - Mean reversion on very short timeframes
    - Volume-weighted price analysis
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        """Initialize HFT strategy.
        
        Args:
            parameters: Strategy parameters including:
                - tick_threshold: Minimum price movement to consider (default: 0.00001)
                - volume_multiplier: Volume spike threshold (default: 2.0)
                - mean_reversion_periods: Periods for mean reversion (default: 5)
                - profit_target: Profit target in pips (default: 0.5)
                - stop_loss: Stop loss in pips (default: 0.3)
                - max_hold_time: Maximum hold time in seconds (default: 300)
                - min_confidence: Minimum confidence for signal (default: 0.4)
                - price_momentum_threshold: Price momentum threshold (default: 0.00005)
        """
        default_params = {
            'tick_threshold': 0.00001,      # 0.1 pip
            'volume_multiplier': 2.0,       # 2x volume spike
            'mean_reversion_periods': 5,    # 5 tick periods
            'profit_target': 0.0005,        # 0.5 pips
            'stop_loss': 0.0003,            # 0.3 pips
            'max_hold_time': 300,           # 5 minutes max
            'min_confidence': 0.4,          # Lower threshold for HFT
            'price_momentum_threshold': 0.00005,  # 0.5 pip momentum
            'spread_threshold': 0.00003,    # Max spread to trade
            'tick_imbalance_threshold': 0.6 # Order flow imbalance
        }
        
        self.parameters = {**default_params, **(parameters or {})}
        self.name = "HFTStrategy"
        
        # HFT-specific state tracking
        self._state = {
            'last_signal_time': None,
            'tick_history': [],             # Last N ticks
            'price_history': [],            # Last N prices
            'volume_history': [],           # Last N volumes
            'bid_ask_history': [],          # Bid/ask spreads
            'momentum_history': [],         # Price momentum
            'signal_count': 0,
            'last_price': None,
            'last_volume': None,
            'avg_volume': None,
            'price_velocity': 0.0,
            'volume_velocity': 0.0,
            'tick_direction': 0,            # +1 uptick, -1 downtick
            'consecutive_ticks': 0,         # Consecutive same direction
            'micro_trend': 'NEUTRAL'        # BULLISH, BEARISH, NEUTRAL
        }
    
    def get_name(self) -> str:
        """Get strategy name."""
        return self.name
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return self.parameters.copy()
    
    def analyze(self, market_data: MarketData) -> Optional[TradingSignal]:
        """Analyze market data for HFT opportunities.
        
        Args:
            market_data: Current tick data with indicators
            
        Returns:
            Trading signal or None if no HFT opportunity
        """
        try:
            current_price = float(market_data.ohlcv.close)
            current_volume = float(market_data.ohlcv.volume)
            
            # Store symbol in state for signal generation
            self._state['symbol'] = market_data.symbol
            
            # Update HFT state
            self._update_hft_state(market_data, current_price, current_volume)
            
            # Check if we have enough tick data
            if not self._has_sufficient_tick_data():
                return None
            
            # HFT signal cooldown (prevent over-trading)
            if self._state['last_signal_time']:
                time_since_last = market_data.timestamp - self._state['last_signal_time']
                if time_since_last < timedelta(seconds=1):  # 1-second cooldown
                    return None
            
            # Generate HFT signal
            signal = self._generate_hft_signal(market_data, current_price, current_volume)
            
            if signal:
                self._state['signal_count'] += 1
                self._state['last_signal_time'] = market_data.timestamp
                logger.info(f"Generated HFT signal: {signal.direction.value} for {signal.symbol}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error in HFT strategy analysis for {market_data.symbol}: {e}")
            return None
    
    def _update_hft_state(self, market_data: MarketData, price: float, volume: float) -> None:
        """Update HFT-specific state with tick data."""
        try:
            # Update price history
            self._state['price_history'].append(price)
            if len(self._state['price_history']) > 20:  # Keep last 20 ticks
                self._state['price_history'].pop(0)
            
            # Update volume history
            self._state['volume_history'].append(volume)
            if len(self._state['volume_history']) > 20:
                self._state['volume_history'].pop(0)
            
            # Calculate tick direction
            if self._state['last_price'] is not None:
                if price > self._state['last_price']:
                    new_tick_direction = 1  # Uptick
                elif price < self._state['last_price']:
                    new_tick_direction = -1  # Downtick
                else:
                    new_tick_direction = 0  # No change
                
                # Update consecutive ticks
                if new_tick_direction == self._state['tick_direction']:
                    self._state['consecutive_ticks'] += 1
                else:
                    self._state['consecutive_ticks'] = 1
                    self._state['tick_direction'] = new_tick_direction
            
            # Calculate price velocity (rate of change)
            if len(self._state['price_history']) >= 3:
                recent_prices = self._state['price_history'][-3:]
                price_changes = [recent_prices[i] - recent_prices[i-1] 
                               for i in range(1, len(recent_prices))]
                self._state['price_velocity'] = sum(price_changes) / len(price_changes)
            
            # Calculate volume velocity
            if len(self._state['volume_history']) >= 3:
                recent_volumes = self._state['volume_history'][-3:]
                volume_changes = [recent_volumes[i] - recent_volumes[i-1] 
                                for i in range(1, len(recent_volumes))]
                self._state['volume_velocity'] = sum(volume_changes) / len(volume_changes)
            
            # Update average volume
            if len(self._state['volume_history']) >= 10:
                self._state['avg_volume'] = sum(self._state['volume_history']) / len(self._state['volume_history'])
            
            # Determine micro-trend
            self._update_micro_trend()
            
            # Update last values
            self._state['last_price'] = price
            self._state['last_volume'] = volume
            
        except Exception as e:
            logger.error(f"Error updating HFT state: {e}")
    
    def _has_sufficient_tick_data(self) -> bool:
        """Check if we have enough tick data for HFT analysis."""
        return (len(self._state['price_history']) >= 5 and 
                len(self._state['volume_history']) >= 5 and
                self._state['avg_volume'] is not None)
    
    def _update_micro_trend(self) -> None:
        """Update micro-trend based on recent price action."""
        if len(self._state['price_history']) < 5:
            return
        
        recent_prices = self._state['price_history'][-5:]
        
        # Calculate micro-trend strength
        price_changes = [recent_prices[i] - recent_prices[i-1] 
                        for i in range(1, len(recent_prices))]
        
        positive_changes = sum(1 for change in price_changes if change > 0)
        negative_changes = sum(1 for change in price_changes if change < 0)
        
        if positive_changes >= 3:
            self._state['micro_trend'] = 'BULLISH'
        elif negative_changes >= 3:
            self._state['micro_trend'] = 'BEARISH'
        else:
            self._state['micro_trend'] = 'NEUTRAL'
    
    def _generate_hft_signal(self, market_data: MarketData, price: float, volume: float) -> Optional[TradingSignal]:
        """Generate HFT signal based on micro-movements and order flow."""
        
        # Calculate volume spike
        volume_spike = volume / self._state['avg_volume'] if self._state['avg_volume'] > 0 else 1.0
        
        # Check spread (don't trade if spread too wide)
        bid = float(market_data.ohlcv.low)   # Approximate bid
        ask = float(market_data.ohlcv.high)  # Approximate ask
        spread = ask - bid
        
        if spread > self.parameters['spread_threshold']:
            return None  # Spread too wide for HFT
        
        # HFT Signal 1: Mean Reversion on Micro-Movements
        mean_reversion_signal = self._check_mean_reversion(price)
        
        # HFT Signal 2: Momentum Breakout
        momentum_signal = self._check_momentum_breakout(price, volume_spike)
        
        # HFT Signal 3: Volume Spike with Price Acceleration
        volume_acceleration_signal = self._check_volume_acceleration(price, volume_spike)
        
        # HFT Signal 4: Tick Imbalance
        tick_imbalance_signal = self._check_tick_imbalance()
        
        # Combine signals
        signals = [mean_reversion_signal, momentum_signal, 
                  volume_acceleration_signal, tick_imbalance_signal]
        valid_signals = [s for s in signals if s is not None]
        
        if not valid_signals:
            return None
        
        # Use the strongest signal
        best_signal = max(valid_signals, key=lambda s: s.strength * s.confidence)
        
        # Final validation
        if best_signal.confidence >= self.parameters['min_confidence']:
            # Add HFT-specific metadata
            best_signal.metadata.update({
                'hft_type': 'micro_movement',
                'volume_spike': volume_spike,
                'price_velocity': self._state['price_velocity'],
                'consecutive_ticks': self._state['consecutive_ticks'],
                'micro_trend': self._state['micro_trend'],
                'spread': spread,
                'profit_target': self.parameters['profit_target'],
                'stop_loss': self.parameters['stop_loss'],
                'max_hold_time': self.parameters['max_hold_time']
            })
            
            return best_signal
        
        return None
    
    def _check_mean_reversion(self, price: float) -> Optional[TradingSignal]:
        """Check for mean reversion opportunities."""
        if len(self._state['price_history']) < self.parameters['mean_reversion_periods']:
            return None
        
        recent_prices = self._state['price_history'][-self.parameters['mean_reversion_periods']:]
        mean_price = sum(recent_prices) / len(recent_prices)
        
        price_deviation = abs(price - mean_price) / mean_price
        
        # If price has deviated significantly, expect reversion
        if price_deviation > self.parameters['tick_threshold']:
            if price > mean_price:
                # Price above mean, expect reversion down
                strength = min(1.0, price_deviation * 100)
                confidence = min(0.8, price_deviation * 50)
                
                return TradingSignal(
                    symbol=self._state.get('symbol', 'UNKNOWN'),
                    direction=SignalDirection.SELL,
                    strength=strength,
                    confidence=confidence,
                    timestamp=datetime.now(),
                    strategy=self.name,
                    metadata={'signal_type': 'mean_reversion_sell'}
                )
            else:
                # Price below mean, expect reversion up
                strength = min(1.0, price_deviation * 100)
                confidence = min(0.8, price_deviation * 50)
                
                return TradingSignal(
                    symbol=self._state.get('symbol', 'UNKNOWN'),
                    direction=SignalDirection.BUY,
                    strength=strength,
                    confidence=confidence,
                    timestamp=datetime.now(),
                    strategy=self.name,
                    metadata={'signal_type': 'mean_reversion_buy'}
                )
        
        return None
    
    def _check_momentum_breakout(self, price: float, volume_spike: float) -> Optional[TradingSignal]:
        """Check for momentum breakout with volume confirmation."""
        if abs(self._state['price_velocity']) < self.parameters['price_momentum_threshold']:
            return None
        
        # Strong momentum with volume spike
        if (abs(self._state['price_velocity']) > self.parameters['price_momentum_threshold'] and
            volume_spike > self.parameters['volume_multiplier']):
            
            if self._state['price_velocity'] > 0:
                # Upward momentum
                strength = min(1.0, abs(self._state['price_velocity']) * 10000)
                confidence = min(0.9, volume_spike / 3.0)
                
                return TradingSignal(
                    symbol=self._state.get('symbol', 'UNKNOWN'),
                    direction=SignalDirection.BUY,
                    strength=strength,
                    confidence=confidence,
                    timestamp=datetime.now(),
                    strategy=self.name,
                    metadata={'signal_type': 'momentum_breakout_buy'}
                )
            else:
                # Downward momentum
                strength = min(1.0, abs(self._state['price_velocity']) * 10000)
                confidence = min(0.9, volume_spike / 3.0)
                
                return TradingSignal(
                    symbol=self._state.get('symbol', 'UNKNOWN'),
                    direction=SignalDirection.SELL,
                    strength=strength,
                    confidence=confidence,
                    timestamp=datetime.now(),
                    strategy=self.name,
                    metadata={'signal_type': 'momentum_breakout_sell'}
                )
        
        return None
    
    def _check_volume_acceleration(self, price: float, volume_spike: float) -> Optional[TradingSignal]:
        """Check for volume acceleration with price movement."""
        if (volume_spike > self.parameters['volume_multiplier'] * 1.5 and
            self._state['volume_velocity'] > 0):
            
            # Volume accelerating, check price direction
            if self._state['consecutive_ticks'] >= 3:
                if self._state['tick_direction'] > 0:
                    # Consecutive upticks with volume
                    strength = min(1.0, volume_spike / 3.0)
                    confidence = min(0.8, self._state['consecutive_ticks'] / 5.0)
                    
                    return TradingSignal(
                        symbol=self._state.get('symbol', 'UNKNOWN'),
                        direction=SignalDirection.BUY,
                        strength=strength,
                        confidence=confidence,
                        timestamp=datetime.now(),
                        strategy=self.name,
                        metadata={'signal_type': 'volume_acceleration_buy'}
                    )
                elif self._state['tick_direction'] < 0:
                    # Consecutive downticks with volume
                    strength = min(1.0, volume_spike / 3.0)
                    confidence = min(0.8, self._state['consecutive_ticks'] / 5.0)
                    
                    return TradingSignal(
                        symbol=self._state.get('symbol', 'UNKNOWN'),
                        direction=SignalDirection.SELL,
                        strength=strength,
                        confidence=confidence,
                        timestamp=datetime.now(),
                        strategy=self.name,
                        metadata={'signal_type': 'volume_acceleration_sell'}
                    )
        
        return None
    
    def _check_tick_imbalance(self) -> Optional[TradingSignal]:
        """Check for order flow imbalance based on tick direction."""
        if self._state['consecutive_ticks'] >= 5:
            # Strong imbalance in one direction
            if self._state['tick_direction'] > 0:
                # Strong buying pressure
                strength = min(1.0, self._state['consecutive_ticks'] / 10.0)
                confidence = min(0.7, self._state['consecutive_ticks'] / 8.0)
                
                return TradingSignal(
                    symbol=self._state.get('symbol', 'UNKNOWN'),
                    direction=SignalDirection.BUY,
                    strength=strength,
                    confidence=confidence,
                    timestamp=datetime.now(),
                    strategy=self.name,
                    metadata={'signal_type': 'tick_imbalance_buy'}
                )
            elif self._state['tick_direction'] < 0:
                # Strong selling pressure
                strength = min(1.0, self._state['consecutive_ticks'] / 10.0)
                confidence = min(0.7, self._state['consecutive_ticks'] / 8.0)
                
                return TradingSignal(
                    symbol=self._state.get('symbol', 'UNKNOWN'),
                    direction=SignalDirection.SELL,
                    strength=strength,
                    confidence=confidence,
                    timestamp=datetime.now(),
                    strategy=self.name,
                    metadata={'signal_type': 'tick_imbalance_sell'}
                )
        
        return None
    
    def reset_state(self) -> None:
        """Reset strategy state."""
        self._state = {
            'last_signal_time': None,
            'tick_history': [],
            'price_history': [],
            'volume_history': [],
            'bid_ask_history': [],
            'momentum_history': [],
            'signal_count': 0,
            'last_price': None,
            'last_volume': None,
            'avg_volume': None,
            'price_velocity': 0.0,
            'volume_velocity': 0.0,
            'tick_direction': 0,
            'consecutive_ticks': 0,
            'micro_trend': 'NEUTRAL'
        }