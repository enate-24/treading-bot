"""
Enhanced HFT Strategy with improved accuracy and risk management.
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np
from collections import deque

from ..models.core import MarketData, TradingSignal
from ..models.enums import SignalDirection
from ..utils.indicators import (
    calculate_ema, calculate_rsi, calculate_macd,
    calculate_adx, calculate_atr, calculate_stochastic,
    calculate_cci,
)

logger = logging.getLogger(__name__)

class EnhancedHFTStrategy:
    """
    Enhanced High-Frequency Trading strategy with:
    - Multi-timeframe analysis
    - Advanced technical indicators
    - Machine learning-inspired scoring
    - Dynamic confidence calculation
    - Better risk/reward optimization
    """
    
    def __init__(self, parameters: Dict = None):
        """Initialize enhanced HFT strategy."""
        self.parameters = parameters or {}
        
        # Enhanced parameters
        self.tick_threshold = self.parameters.get('tick_threshold', 0.000003)
        self.volume_multiplier = self.parameters.get('volume_multiplier', 1.5)
        self.spread_threshold = self.parameters.get('spread_threshold', 0.00002)
        self.min_confidence = self.parameters.get('min_confidence', 0.65)   # raised: require strong agreement
        self.profit_target = self.parameters.get('profit_target', 0.0008)   # ~$3.2 on XAUUSD @4000
        self.stop_loss = self.parameters.get('stop_loss', 0.0005)           # ~$2 on XAUUSD @4000
        self.max_hold_time = self.parameters.get('max_hold_time', 600)

        # Advanced parameters
        self.trend_strength_threshold = self.parameters.get('trend_strength_threshold', 0.6)
        self.momentum_periods = self.parameters.get('momentum_periods', [5, 10, 20])
        self.volatility_window = self.parameters.get('volatility_window', 20)
        self.min_risk_reward = self.parameters.get('min_risk_reward', 1.5)
        self.signal_cooldown_seconds = self.parameters.get('signal_cooldown_seconds', 60)  # 1 min between signals
        self.min_signals_required = self.parameters.get('min_signals_required', 3)         # need 3/5 layers to agree
        
        # State tracking
        self._state = {
            'symbol': None,
            'tick_history': deque(maxlen=200),
            'price_history': deque(maxlen=200),
            'volume_history': deque(maxlen=200),
            'signal_count': 0,
            'last_signal_time': None,
            'avg_volume': 0,
            'volatility': 0,
            'trend_direction': 0,
            'trend_strength': 0,
            'support_levels': [],
            'resistance_levels': []
        }
        
        logger.info("Enhanced HFT Strategy initialized with improved accuracy")
    
    def analyze(self, market_data: MarketData) -> Optional[TradingSignal]:
        """
        Analyze market data with enhanced accuracy.
        
        Args:
            market_data: Current market data with indicators
            
        Returns:
            Trading signal or None
        """
        try:
            current_price = float(market_data.ohlcv.close)
            current_volume = float(market_data.ohlcv.volume)
            
            # Update state
            self._state['symbol'] = market_data.symbol
            self._update_state(market_data, current_price, current_volume)
            
            # Check if we have enough data
            if len(self._state['price_history']) < 50:
                return None
            
            # Signal cooldown
            if self._state['last_signal_time']:
                time_since_last = market_data.timestamp - self._state['last_signal_time']
                if time_since_last < timedelta(seconds=self.signal_cooldown_seconds):
                    return None
            
            # Multi-layer analysis
            trend_signal = self._analyze_trend(market_data, current_price)
            momentum_signal = self._analyze_momentum(current_price)
            volume_signal = self._analyze_volume(current_volume)
            volatility_signal = self._analyze_volatility(current_price)
            support_resistance_signal = self._analyze_support_resistance(current_price)

            # --- Indicator conflict check using market_data indicators ---
            indicators = market_data.indicators or {}
            if not self._indicators_agree(indicators):
                return None

            # Combine signals with weighted scoring
            signals = [
                (trend_signal, 0.30),
                (momentum_signal, 0.25),
                (volume_signal, 0.20),
                (volatility_signal, 0.15),
                (support_resistance_signal, 0.10)
            ]

            # Count how many layers fired and in which direction
            buy_count = sum(1 for s, _ in signals if s and s.direction == SignalDirection.BUY)
            sell_count = sum(1 for s, _ in signals if s and s.direction == SignalDirection.SELL)

            # Require minimum number of agreeing signals
            if buy_count < self.min_signals_required and sell_count < self.min_signals_required:
                return None

            # Calculate weighted score
            buy_score = 0
            sell_score = 0
            total_weight = 0

            for signal, weight in signals:
                if signal:
                    total_weight += weight
                    if signal.direction == SignalDirection.BUY:
                        buy_score += signal.confidence * weight
                    else:
                        sell_score += signal.confidence * weight

            if total_weight == 0:
                return None

            buy_score = buy_score / total_weight if total_weight > 0 else 0
            sell_score = sell_score / total_weight if total_weight > 0 else 0

            # Choose direction with higher score
            if buy_score > sell_score and buy_score >= self.min_confidence:
                direction = SignalDirection.BUY
                confidence = buy_score
                strength = min(buy_score * 1.2, 1.0)
            elif sell_score > buy_score and sell_score >= self.min_confidence:
                direction = SignalDirection.SELL
                confidence = sell_score
                strength = min(sell_score * 1.2, 1.0)
            else:
                return None
            
            # Calculate dynamic stop loss and take profit
            volatility = self._state['volatility']
            atr_multiplier = 1.5 if volatility > 0.0001 else 1.0
            
            stop_loss_pct = self.stop_loss * atr_multiplier
            profit_target_pct = stop_loss_pct * self.min_risk_reward
            
            # Create signal
            signal = TradingSignal(
                symbol=market_data.symbol,
                direction=direction,
                strength=strength,
                confidence=confidence,
                timestamp=market_data.timestamp,
                strategy='enhanced_hft',
                metadata={
                    'strategy': 'enhanced_hft',
                    'entry_price': current_price,
                    'stop_loss': stop_loss_pct,
                    'profit_target': profit_target_pct,
                    'max_hold_time': self.max_hold_time,
                    'trend_strength': self._state['trend_strength'],
                    'volatility': volatility,
                    'volume_spike': current_volume / self._state['avg_volume'] if self._state['avg_volume'] > 0 else 1.0,
                    'risk_reward_ratio': self.min_risk_reward,
                    'signal_sources': {
                        'trend': trend_signal is not None,
                        'momentum': momentum_signal is not None,
                        'volume': volume_signal is not None,
                        'volatility': volatility_signal is not None,
                        'support_resistance': support_resistance_signal is not None
                    }
                }
            )
            
            self._state['signal_count'] += 1
            self._state['last_signal_time'] = market_data.timestamp
            
            logger.info(f"Enhanced HFT signal generated: {direction.value} {market_data.symbol}")
            logger.info(f"  Confidence: {confidence:.2%}, Strength: {strength:.2f}")
            logger.info(f"  Trend: {self._state['trend_strength']:.2f}, Volatility: {volatility:.5f}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error in enhanced HFT analysis: {e}", exc_info=True)
            return None
    
    def _update_state(self, market_data: MarketData, price: float, volume: float):
        """Update strategy state with new data."""
        # Update histories
        self._state['tick_history'].append({
            'price': price,
            'volume': volume,
            'timestamp': market_data.timestamp
        })

        self._state['price_history'].append(price)
        self._state['volume_history'].append(volume)

        # Calculate average volume
        if len(self._state['volume_history']) >= 20:
            self._state['avg_volume'] = np.mean(list(self._state['volume_history'])[-20:])

        # Calculate volatility (ATR-like)
        if len(self._state['price_history']) >= self.volatility_window:
            prices = np.array(self._state['price_history'])
            self._state['volatility'] = np.std(prices)

        # Update support/resistance levels
        self._update_support_resistance()
    
    def _analyze_trend(self, market_data: MarketData, current_price: float) -> Optional[TradingSignal]:
        """Analyze trend using multiple EMAs."""
        try:
            if len(self._state['price_history']) < 50:
                return None
            
            prices = np.array(self._state['price_history'])
            
            # Calculate EMAs
            ema_fast = calculate_ema(prices, 10)
            ema_medium = calculate_ema(prices, 20)
            ema_slow = calculate_ema(prices, 50)
            
            # Trend direction
            if ema_fast > ema_medium > ema_slow:
                trend_direction = 1  # Uptrend
                direction = SignalDirection.BUY
            elif ema_fast < ema_medium < ema_slow:
                trend_direction = -1  # Downtrend
                direction = SignalDirection.SELL
            else:
                return None
            
            # Trend strength (0-1)
            ema_spread = abs(ema_fast - ema_slow) / ema_slow
            trend_strength = min(ema_spread / 0.001, 1.0)  # Normalize
            
            # Price position relative to EMAs
            price_above_fast = current_price > ema_fast
            price_above_medium = current_price > ema_medium
            
            # Confidence based on alignment
            if trend_direction == 1 and price_above_fast and price_above_medium:
                confidence = 0.7 + (trend_strength * 0.3)
            elif trend_direction == -1 and not price_above_fast and not price_above_medium:
                confidence = 0.7 + (trend_strength * 0.3)
            else:
                confidence = 0.5
            
            self._state['trend_direction'] = trend_direction
            self._state['trend_strength'] = trend_strength
            
            if confidence >= 0.6:
                return TradingSignal(
                    symbol=market_data.symbol,
                    direction=direction,
                    strength=trend_strength,
                    confidence=confidence,
                    timestamp=market_data.timestamp,
                    strategy='enhanced_hft',
                    metadata={'source': 'trend'}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in trend analysis: {e}")
            return None
    
    def _analyze_momentum(self, current_price: float) -> Optional[TradingSignal]:
        """Analyze momentum using multiple periods."""
        try:
            if len(self._state['price_history']) < 20:
                return None
            
            prices = np.array(self._state['price_history'])
            
            # Calculate momentum for different periods
            momentum_scores = []
            for period in self.momentum_periods:
                if len(prices) >= period:
                    momentum = (prices[-1] - prices[-period]) / prices[-period]
                    momentum_scores.append(momentum)
            
            if not momentum_scores:
                return None
            
            # Average momentum
            avg_momentum = np.mean(momentum_scores)
            momentum_strength = abs(avg_momentum)
            
            # Direction
            if avg_momentum > 0.00005:  # 0.5 pips
                direction = SignalDirection.BUY
                confidence = min(momentum_strength / 0.0002, 1.0)
            elif avg_momentum < -0.00005:
                direction = SignalDirection.SELL
                confidence = min(momentum_strength / 0.0002, 1.0)
            else:
                return None
            
            if confidence >= 0.5:
                return TradingSignal(
                    symbol=self._state['symbol'],
                    direction=direction,
                    strength=min(momentum_strength * 100, 1.0),
                    confidence=confidence,
                    timestamp=datetime.now(),
                    strategy='enhanced_hft',
                    metadata={'source': 'momentum'}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in momentum analysis: {e}")
            return None
    
    def _analyze_volume(self, current_volume: float) -> Optional[TradingSignal]:
        """Analyze volume patterns."""
        try:
            if self._state['avg_volume'] == 0 or len(self._state['volume_history']) < 10:
                return None
            
            volume_ratio = current_volume / self._state['avg_volume']
            
            # Volume spike with price movement
            if volume_ratio >= self.volume_multiplier:
                recent_prices = list(self._state['price_history'])[-5:]
                price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
                
                if price_change > 0.00003:  # 0.3 pips
                    direction = SignalDirection.BUY
                    confidence = min(volume_ratio / 2.0, 1.0)
                elif price_change < -0.00003:
                    direction = SignalDirection.SELL
                    confidence = min(volume_ratio / 2.0, 1.0)
                else:
                    return None
                
                if confidence >= 0.5:
                    return TradingSignal(
                        symbol=self._state['symbol'],
                        direction=direction,
                        strength=min(volume_ratio / 2.0, 1.0),
                        confidence=confidence,
                        timestamp=datetime.now(),
                        strategy='enhanced_hft',
                        metadata={'source': 'volume'}
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in volume analysis: {e}")
            return None
    
    def _analyze_volatility(self, current_price: float) -> Optional[TradingSignal]:
        """Analyze volatility for breakout opportunities."""
        try:
            if self._state['volatility'] == 0:
                return None
            
            # Convert deque to list before slicing
            price_list = list(self._state['price_history'])

            # Check for volatility expansion
            recent_volatility = np.std(price_list[-10:])
            volatility_ratio = recent_volatility / self._state['volatility']
            
            if volatility_ratio > 1.3:  # 30% increase in volatility
                # Determine direction from recent price action
                recent_change = (price_list[-1] - price_list[-5]) / price_list[-5]
                
                if recent_change > 0:
                    direction = SignalDirection.BUY
                else:
                    direction = SignalDirection.SELL
                
                confidence = min(volatility_ratio / 2.0, 0.8)
                
                return TradingSignal(
                    symbol=self._state['symbol'],
                    direction=direction,
                    strength=min(volatility_ratio / 2.0, 1.0),
                    confidence=confidence,
                    timestamp=datetime.now(),
                    strategy='enhanced_hft',
                    metadata={'source': 'volatility'}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in volatility analysis: {e}")
            return None
    
    def _analyze_support_resistance(self, current_price: float) -> Optional[TradingSignal]:
        """Analyze support and resistance levels."""
        try:
            if not self._state['support_levels'] or not self._state['resistance_levels']:
                return None
            
            # Find nearest support and resistance
            nearest_support = max([s for s in self._state['support_levels'] if s < current_price], default=None)
            nearest_resistance = min([r for r in self._state['resistance_levels'] if r > current_price], default=None)
            
            if nearest_support and nearest_resistance:
                # Distance to levels
                dist_to_support = (current_price - nearest_support) / current_price
                dist_to_resistance = (nearest_resistance - current_price) / current_price
                
                # Bounce from support
                if dist_to_support < 0.0001:  # Within 1 pip of support
                    return TradingSignal(
                        symbol=self._state['symbol'],
                        direction=SignalDirection.BUY,
                        strength=0.7,
                        confidence=0.7,
                        timestamp=datetime.now(),
                        strategy='enhanced_hft',
                        metadata={'source': 'support_bounce'}
                    )
                
                # Rejection from resistance
                if dist_to_resistance < 0.0001:  # Within 1 pip of resistance
                    return TradingSignal(
                        symbol=self._state['symbol'],
                        direction=SignalDirection.SELL,
                        strength=0.7,
                        confidence=0.7,
                        timestamp=datetime.now(),
                        strategy='enhanced_hft',
                        metadata={'source': 'resistance_rejection'}
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in support/resistance analysis: {e}")
            return None
    
    def _update_support_resistance(self):
        """Update support and resistance levels."""
        try:
            if len(self._state['price_history']) < 50:
                return
            
            # Convert deque to numpy array before slicing
            prices = np.array(list(self._state['price_history'])[-50:])
            
            # Find local minima (support)
            supports = []
            for i in range(2, len(prices) - 2):
                if prices[i] < prices[i-1] and prices[i] < prices[i-2] and \
                   prices[i] < prices[i+1] and prices[i] < prices[i+2]:
                    supports.append(prices[i])
            
            # Find local maxima (resistance)
            resistances = []
            for i in range(2, len(prices) - 2):
                if prices[i] > prices[i-1] and prices[i] > prices[i-2] and \
                   prices[i] > prices[i+1] and prices[i] > prices[i+2]:
                    resistances.append(prices[i])
            
            self._state['support_levels'] = sorted(set(supports))[-3:]  # Keep top 3
            self._state['resistance_levels'] = sorted(set(resistances))[:3]  # Keep top 3
            
        except Exception as e:
            logger.error(f"Error updating support/resistance: {e}")
    
    def _indicators_agree(self, indicators: dict) -> bool:
        """
        Check that key indicators don't contradict each other.
        Requires at least 70% of indicator votes to agree on one direction.
        """
        if not indicators:
            return False

        votes_buy = 0
        votes_sell = 0

        # RSI
        rsi = indicators.get('rsi')
        if rsi is not None:
            if rsi < 45:
                votes_sell += 1
            elif rsi > 55:
                votes_buy += 1

        # MACD value
        macd = indicators.get('macd')
        if macd is not None:
            if macd < 0:
                votes_sell += 1
            elif macd > 0:
                votes_buy += 1

        # MACD crossover
        macd_signal = indicators.get('macd_signal')
        if macd is not None and macd_signal is not None:
            if macd > macd_signal:
                votes_buy += 1
            elif macd < macd_signal:
                votes_sell += 1

        # Stochastic crossover from extremes only
        stoch_k = indicators.get('stoch_k')
        stoch_d = indicators.get('stoch_d')
        if stoch_k is not None and stoch_d is not None:
            if stoch_k < 25 and stoch_k > stoch_d:
                votes_buy += 1
            elif stoch_k > 75 and stoch_k < stoch_d:
                votes_sell += 1

        # EMA crossover
        ema_12 = indicators.get('ema_12')
        ema_26 = indicators.get('ema_26')
        if ema_12 is not None and ema_26 is not None:
            if ema_12 > ema_26:
                votes_buy += 1
            elif ema_12 < ema_26:
                votes_sell += 1

        total_votes = votes_buy + votes_sell
        if total_votes < 3:
            return False

        buy_ratio = votes_buy / total_votes
        sell_ratio = votes_sell / total_votes
        return buy_ratio >= 0.70 or sell_ratio >= 0.70

    def get_name(self) -> str:
        """Get strategy name."""
        return "EnhancedHFTStrategy"

    def _analyze_indicators(self, market_data: MarketData) -> Optional[TradingSignal]:
        """Analyze using multiple technical indicators."""
        try:
            indicators = market_data.indicators
            if not indicators:
                return None
            
            current_price = float(market_data.ohlcv.close)
            signals = []
            
            # MACD Signal
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            macd_histogram = indicators.get('macd_histogram', 0)
            
            if macd > macd_signal and macd_histogram > 0:
                signals.append(('BUY', 0.7, 'MACD'))
            elif macd < macd_signal and macd_histogram < 0:
                signals.append(('SELL', 0.7, 'MACD'))
            
            # RSI Signal
            rsi = indicators.get('rsi', 50)
            if rsi < 30:
                signals.append(('BUY', 0.8, 'RSI_Oversold'))
            elif rsi > 70:
                signals.append(('SELL', 0.8, 'RSI_Overbought'))
            # Removed weak RSI signals (40-60) — they generate noise
            
            # Bollinger Bands Signal
            bb_upper = indicators.get('bb_upper', 0)
            bb_lower = indicators.get('bb_lower', 0)
            bb_middle = indicators.get('bb_middle', 0)
            
            if bb_upper > 0 and bb_lower > 0:
                if current_price <= bb_lower:
                    signals.append(('BUY', 0.75, 'BB_Lower'))
                elif current_price >= bb_upper:
                    signals.append(('SELL', 0.75, 'BB_Upper'))
                # Removed middle-band signals — too noisy
            
            # Stochastic Signal
            stoch_k = indicators.get('stoch_k', 50)
            stoch_d = indicators.get('stoch_d', 50)
            
            if stoch_k < 20 and stoch_k > stoch_d:
                signals.append(('BUY', 0.7, 'Stoch_Oversold'))
            elif stoch_k > 80 and stoch_k < stoch_d:
                signals.append(('SELL', 0.7, 'Stoch_Overbought'))
            
            # ADX Signal (trend strength)
            adx = indicators.get('adx', 25)
            if adx > 25:  # Strong trend
                # Use EMA crossover for direction
                ema_12 = indicators.get('ema_12', 0)
                ema_26 = indicators.get('ema_26', 0)
                if ema_12 > ema_26:
                    signals.append(('BUY', 0.6, 'ADX_Trend'))
                elif ema_12 < ema_26:
                    signals.append(('SELL', 0.6, 'ADX_Trend'))
            
            # CCI Signal
            cci = indicators.get('cci', 0)
            if cci < -100:
                signals.append(('BUY', 0.65, 'CCI_Oversold'))
            elif cci > 100:
                signals.append(('SELL', 0.65, 'CCI_Overbought'))
            
            # Aggregate signals
            if not signals:
                return None
            
            buy_signals = [(conf, src) for dir, conf, src in signals if dir == 'BUY']
            sell_signals = [(conf, src) for dir, conf, src in signals if dir == 'SELL']
            
            buy_score = sum(conf for conf, _ in buy_signals) / len(signals) if buy_signals else 0
            sell_score = sum(conf for conf, _ in sell_signals) / len(signals) if sell_signals else 0
            
            if buy_score > sell_score and buy_score >= 0.60:
                direction = SignalDirection.BUY
                confidence = min(buy_score, 1.0)
                sources = [src for _, src in buy_signals]
            elif sell_score > buy_score and sell_score >= 0.60:
                direction = SignalDirection.SELL
                confidence = min(sell_score, 1.0)
                sources = [src for _, src in sell_signals]
            else:
                return None
            
            return TradingSignal(
                symbol=market_data.symbol,
                direction=direction,
                strength=confidence,
                confidence=confidence,
                timestamp=market_data.timestamp,
                strategy='enhanced_hft',
                metadata={
                    'source': 'indicators',
                    'indicator_signals': sources,
                    'rsi': rsi,
                    'macd': macd,
                    'adx': adx,
                    'stoch_k': stoch_k,
                    'cci': cci
                }
            )
            
        except Exception as e:
            logger.error(f"Error analyzing indicators: {e}")
            return None
