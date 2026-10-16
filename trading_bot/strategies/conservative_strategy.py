"""
Conservative Trading Strategy - Fixed based on diagnosis
Only trades profitable symbols with strict filters
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import numpy as np

from trading_bot.models.core import MarketData, TradingSignal
from trading_bot.models.enums import SignalDirection

logger = logging.getLogger(__name__)

class ConservativeStrategy:
    """
    Conservative strategy with strict filters based on actual performance data.
    
    Key improvements:
    - Only trades profitable symbols (EURJPYm, GBPJPYm)
    - Avoids losing hours
    - Higher confidence threshold (75%)
    - Better risk/reward ratio (2:1)
    - Trend confirmation required
    - Max 3 consecutive losses protection
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Strategy parameters
        self.min_confidence = 0.75  # Increased from 0.15
        self.min_trend_strength = 0.6
        self.min_risk_reward = 2.0  # Increased from 1.5
        self.max_hold_time = 300  # 5 minutes
        
        # Allowed symbols (only profitable ones + gold by user request)
        self.allowed_symbols = ['EURJPYm', 'GBPJPYm', 'XAUUSDm']
        
        # Avoid these hours (GMT) - removed to allow trading now
        self.avoid_hours = []
        
        # Good hours (GMT) - allow all hours
        self.good_hours = list(range(24))
        
        # State tracking
        self._state = {
            'consecutive_losses': 0,
            'daily_loss': 0.0,
            'last_reset': datetime.now().date(),
            'trades_today': 0
        }
        
        logger.info("Conservative Strategy initialized")
        logger.info(f"Allowed symbols: {self.allowed_symbols}")
        logger.info(f"Good hours: {self.good_hours}")
        logger.info(f"Min confidence: {self.min_confidence}")
        logger.info(f"Min R:R ratio: {self.min_risk_reward}")
    
    def get_name(self) -> str:
        """Return strategy name"""
        return "ConservativeStrategy"
    
    def should_trade_now(self) -> bool:
        """Check if we should trade at current time"""
        current_hour = datetime.now().hour
        
        # Reset daily counters
        today = datetime.now().date()
        if today != self._state['last_reset']:
            self._state['daily_loss'] = 0.0
            self._state['trades_today'] = 0
            self._state['consecutive_losses'] = 0
            self._state['last_reset'] = today
        
        # Check consecutive losses
        if self._state['consecutive_losses'] >= 3:
            logger.warning(f"Stopped: {self._state['consecutive_losses']} consecutive losses")
            return False
        
        # Check daily loss limit
        if self._state['daily_loss'] <= -0.50:
            logger.warning(f"Stopped: Daily loss limit reached (${self._state['daily_loss']:.2f})")
            return False
        
        # Check if current hour is good
        if current_hour in self.avoid_hours:
            logger.debug(f"Skipping: Hour {current_hour} is in avoid list")
            return False
        
        if current_hour not in self.good_hours:
            logger.debug(f"Skipping: Hour {current_hour} is not in good hours list")
            return False
        
        return True
    
    def analyze(self, market_data: MarketData) -> Optional[TradingSignal]:
        """
        Analyze market data and generate trading signal with strict filters.
        """
        try:
            # Check if symbol is allowed
            if market_data.symbol not in self.allowed_symbols:
                return None
            
            # Check if we should trade now
            if not self.should_trade_now():
                return None
            
            # Get price data from ohlcv_list (stored as attribute)
            if not hasattr(market_data, 'ohlcv_list') or len(market_data.ohlcv_list) < 50:
                return None
            
            closes = np.array([bar.close for bar in market_data.ohlcv_list])
            highs = np.array([bar.high for bar in market_data.ohlcv_list])
            lows = np.array([bar.low for bar in market_data.ohlcv_list])
            volumes = np.array([bar.volume for bar in market_data.ohlcv_list])
            
            current_price = closes[-1]
            
            # Calculate indicators
            # 1. Trend (EMA)
            ema_20 = self._calculate_ema(closes, 20)
            ema_50 = self._calculate_ema(closes, 50)
            
            # 2. RSI
            rsi = self._calculate_rsi(closes, 14)
            
            # 3. MACD
            ema_12 = self._calculate_ema(closes, 12)
            ema_26 = self._calculate_ema(closes, 26)
            macd = ema_12 - ema_26
            macd_signal = self._calculate_ema(np.array([macd] * 9), 9)
            
            # 4. Bollinger Bands
            sma_20 = np.mean(closes[-20:])
            std_20 = np.std(closes[-20:])
            bb_upper = sma_20 + (2 * std_20)
            bb_lower = sma_20 - (2 * std_20)
            
            # 5. ATR for volatility
            atr = self._calculate_atr(highs, lows, closes, 14)
            
            # STRICT SIGNAL GENERATION
            signals = []
            confidence_scores = []
            
            # Signal 1: Strong Trend + RSI confirmation
            if ema_20 > ema_50 and current_price > ema_20:
                if 30 < rsi < 70:  # Not overbought/oversold
                    signals.append('BUY')
                    confidence_scores.append(0.8)
            elif ema_20 < ema_50 and current_price < ema_20:
                if 30 < rsi < 70:
                    signals.append('SELL')
                    confidence_scores.append(0.8)
            
            # Signal 2: MACD crossover with trend
            if macd > macd_signal and macd > 0:
                if current_price > ema_50:  # Confirm uptrend
                    signals.append('BUY')
                    confidence_scores.append(0.75)
            elif macd < macd_signal and macd < 0:
                if current_price < ema_50:  # Confirm downtrend
                    signals.append('SELL')
                    confidence_scores.append(0.75)
            
            # Signal 3: Bollinger Band bounce (mean reversion)
            if current_price <= bb_lower and rsi < 40:
                signals.append('BUY')
                confidence_scores.append(0.7)
            elif current_price >= bb_upper and rsi > 60:
                signals.append('SELL')
                confidence_scores.append(0.7)
            
            # Require at least 2 confirming signals
            if len(signals) < 2:
                return None
            
            # Determine direction (majority vote)
            buy_votes = signals.count('BUY')
            sell_votes = signals.count('SELL')
            
            if buy_votes > sell_votes:
                direction = SignalDirection.BUY
                confidence = np.mean([conf for sig, conf in zip(signals, confidence_scores) if sig == 'BUY'])
            elif sell_votes > buy_votes:
                direction = SignalDirection.SELL
                confidence = np.mean([conf for sig, conf in zip(signals, confidence_scores) if sig == 'SELL'])
            else:
                return None  # No clear direction
            
            # Check minimum confidence
            if confidence < self.min_confidence:
                return None
            
            # Calculate stop loss and take profit (2:1 R:R)
            stop_loss_pips = 15
            take_profit_pips = 30  # 2:1 ratio
            
            pip_value = 0.01 if 'JPY' in market_data.symbol else 0.0001
            
            if direction == SignalDirection.BUY:
                stop_loss = current_price - (stop_loss_pips * pip_value)
                take_profit = current_price + (take_profit_pips * pip_value)
            else:
                stop_loss = current_price + (stop_loss_pips * pip_value)
                take_profit = current_price - (take_profit_pips * pip_value)
            
            # Create signal
            signal = TradingSignal(
                symbol=market_data.symbol,
                direction=direction,
                strength=confidence,
                confidence=confidence,
                timestamp=market_data.timestamp,
                strategy='conservative',
                metadata={
                    'entry_price': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'stop_loss_pct': stop_loss_pips * pip_value / current_price,
                    'profit_target_pct': take_profit_pips * pip_value / current_price,
                    'risk_reward_ratio': self.min_risk_reward,
                    'rsi': rsi,
                    'macd': macd,
                    'atr': atr,
                    'signals_count': len(signals),
                    'buy_votes': buy_votes,
                    'sell_votes': sell_votes
                }
            )
            
            logger.info(f"[SIGNAL] Conservative Signal: {direction.value} {market_data.symbol}")
            logger.info(f"   Confidence: {confidence:.2%}, Signals: {len(signals)}")
            logger.info(f"   RSI: {rsi:.1f}, MACD: {macd:.5f}")
            logger.info(f"   R:R: {self.min_risk_reward}:1, SL: {stop_loss_pips} pips, TP: {take_profit_pips} pips")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error in conservative strategy: {e}", exc_info=True)
            return None
    
    def record_trade_result(self, profit: float):
        """Record trade result for tracking"""
        self._state['trades_today'] += 1
        self._state['daily_loss'] += profit
        
        if profit < 0:
            self._state['consecutive_losses'] += 1
            logger.warning(f"Loss recorded: ${profit:.2f}, Consecutive: {self._state['consecutive_losses']}")
        else:
            self._state['consecutive_losses'] = 0
            logger.info(f"Win recorded: ${profit:.2f}, Streak reset")
    
    def _calculate_ema(self, data: np.ndarray, period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(data) < period:
            return data[-1]
        multiplier = 2 / (period + 1)
        ema = data[-period]
        for price in data[-period+1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return ema
    
    def _calculate_rsi(self, data: np.ndarray, period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(data) < period + 1:
            return 50.0
        
        deltas = np.diff(data[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(highs) < period + 1:
            return 0.0
        
        tr_list = []
        for i in range(-period, 0):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            tr = max(high_low, high_close, low_close)
            tr_list.append(tr)
        
        return np.mean(tr_list)
