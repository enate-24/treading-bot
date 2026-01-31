"""Data Handler implementation for market data processing."""

import asyncio
import json
import logging
import websockets
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Callable, Any
from collections import deque, defaultdict
import pandas as pd
import numpy as np
from threading import Lock, Thread
import time

from .interfaces.data_handler import IDataHandler
from .models import Price, MarketData, OHLCV


logger = logging.getLogger(__name__)


class DataHandler(IDataHandler):
    """Concrete implementation of data handler for market data processing."""
    
    def __init__(self, max_history_size: int = 1000):
        """Initialize the data handler.
        
        Args:
            max_history_size: Maximum number of data points to keep in memory
        """
        self.max_history_size = max_history_size
        self._subscriptions: Dict[str, Dict[str, Any]] = {}
        self._price_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_size))
        self._indicators: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._callbacks: List[Callable[[MarketData], None]] = []
        self._websocket_connections: Dict[str, Any] = {}
        self._lock = Lock()
        self._running = False
        self._update_thread: Optional[Thread] = None
        
        # Technical indicator parameters
        self._indicator_params = {
            'RSI': {'period': 14},
            'SMA_20': {'period': 20},
            'SMA_50': {'period': 50},
            'EMA_12': {'period': 12},
            'EMA_26': {'period': 26},
            'MACD': {'fast': 12, 'slow': 26, 'signal': 9}
        }
    
    def subscribe_to_symbol(self, symbol: str, timeframe: str) -> None:
        """Subscribe to real-time data for a trading symbol."""
        with self._lock:
            if symbol not in self._subscriptions:
                self._subscriptions[symbol] = {}
            
            self._subscriptions[symbol][timeframe] = {
                'active': True,
                'last_update': None
            }
            
            logger.info(f"Subscribed to {symbol} on {timeframe} timeframe")
            
            # Start data processing if not already running
            if not self._running:
                self._start_data_processing()
    
    def get_latest_price(self, symbol: str) -> Optional[Price]:
        """Get the latest price data for a symbol."""
        with self._lock:
            if symbol not in self._price_data or not self._price_data[symbol]:
                return None
            
            latest_data = self._price_data[symbol][-1]
            return Price(
                symbol=symbol,
                timestamp=latest_data['timestamp'],
                bid=latest_data['bid'],
                ask=latest_data['ask'],
                last=latest_data['last'],
                volume=latest_data['volume']
            )
    
    def get_indicator_value(self, symbol: str, indicator: str) -> Optional[float]:
        """Get the latest value of a technical indicator."""
        with self._lock:
            if symbol in self._indicators and indicator in self._indicators[symbol]:
                return self._indicators[symbol][indicator]
            return None
    
    def get_historical_data(self, symbol: str, periods: int) -> pd.DataFrame:
        """Get historical market data for backtesting."""
        with self._lock:
            if symbol not in self._price_data:
                return pd.DataFrame()
            
            data_points = list(self._price_data[symbol])
            if not data_points:
                return pd.DataFrame()
            
            # Get the requested number of periods (or all available if less)
            start_idx = max(0, len(data_points) - periods)
            selected_data = data_points[start_idx:]
            
            # Convert to DataFrame while preserving Decimal precision
            df_data = []
            for point in selected_data:
                df_data.append({
                    'timestamp': point['timestamp'],
                    'open': point['open'],  # Keep as Decimal
                    'high': point['high'],  # Keep as Decimal
                    'low': point['low'],    # Keep as Decimal
                    'close': point['last'], # Keep as Decimal
                    'volume': point['volume'] # Keep as Decimal
                })
            
            df = pd.DataFrame(df_data)
            if not df.empty:
                df.set_index('timestamp', inplace=True)
                
                # Convert Decimal columns to float64 with high precision
                # This preserves precision better than direct float() conversion
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    if col in df.columns:
                        # Convert Decimal to string then to float64 for better precision
                        df[col] = df[col].apply(lambda x: float(str(x)) if x is not None else 0.0)
                        df[col] = df[col].astype('float64')
            
            return df
    
    def register_data_callback(self, callback: Callable[[MarketData], None]) -> None:
        """Register callback for real-time market data updates."""
        with self._lock:
            self._callbacks.append(callback)
            callback_name = getattr(callback, '__name__', str(callback))
            logger.info(f"Registered data callback: {callback_name}")
    
    def _start_data_processing(self) -> None:
        """Start the data processing thread."""
        if self._running:
            return
        
        self._running = True
        self._update_thread = Thread(target=self._data_processing_loop, daemon=True)
        self._update_thread.start()
        logger.info("Started data processing thread")
    
    def _data_processing_loop(self) -> None:
        """Main data processing loop (simulated for now)."""
        while self._running:
            try:
                # Simulate receiving market data for subscribed symbols
                with self._lock:
                    symbols = list(self._subscriptions.keys())
                
                for symbol in symbols:
                    # Generate simulated market data
                    market_data = self._generate_simulated_data(symbol)
                    if market_data:
                        self._process_market_data(market_data)
                
                time.sleep(1)  # Update every second
                
            except Exception as e:
                logger.error(f"Error in data processing loop: {e}")
                time.sleep(5)  # Wait before retrying
    
    def _generate_simulated_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Generate simulated market data for testing purposes."""
        try:
            # Get last price or start with a base price
            last_price = Decimal('50000.00')  # Default BTC price
            if symbol in self._price_data and self._price_data[symbol]:
                last_price = self._price_data[symbol][-1]['last']
            
            # Generate realistic price movement (±0.1%)
            price_change = float(last_price) * (np.random.random() - 0.5) * 0.002
            new_price = last_price + Decimal(str(round(price_change, 2)))
            
            # Ensure price doesn't go negative
            new_price = max(new_price, Decimal('0.01'))
            
            # Generate bid/ask spread (0.01-0.05%)
            spread_pct = np.random.uniform(0.0001, 0.0005)
            spread = new_price * Decimal(str(spread_pct))
            
            bid = new_price - spread / 2
            ask = new_price + spread / 2
            
            # Generate volume
            volume = Decimal(str(round(np.random.uniform(0.1, 10.0), 4)))
            
            return {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'open': new_price,
                'high': new_price * Decimal('1.001'),
                'low': new_price * Decimal('0.999'),
                'last': new_price,
                'bid': bid,
                'ask': ask,
                'volume': volume
            }
            
        except Exception as e:
            logger.error(f"Error generating simulated data for {symbol}: {e}")
            return None
    
    def _process_market_data(self, raw_data: Dict[str, Any]) -> None:
        """Process incoming market data and update indicators."""
        try:
            # Validate input data structure
            if not self._validate_market_data(raw_data):
                logger.warning(f"Invalid market data rejected: {raw_data}")
                return
            
            symbol = raw_data['symbol']
            
            # Store the raw data
            self._price_data[symbol].append(raw_data)
            
            # Calculate technical indicators
            self._update_indicators(symbol)
            
            # Create MarketData object
            ohlcv = OHLCV(
                open=raw_data['open'],
                high=raw_data['high'],
                low=raw_data['low'],
                close=raw_data['last'],
                volume=raw_data['volume']
            )
            
            market_data = MarketData(
                symbol=symbol,
                timestamp=raw_data['timestamp'],
                ohlcv=ohlcv,
                indicators=self._indicators[symbol].copy()
            )
            
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(market_data)
                except Exception as e:
                    logger.error(f"Error in data callback {callback.__name__}: {e}")
            
        except Exception as e:
            logger.error(f"Error processing market data: {e}")
    
    def _validate_market_data(self, raw_data: Any) -> bool:
        """Validate incoming market data for completeness and correctness.
        
        Args:
            raw_data: Raw market data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        try:
            # Check if data is a dictionary
            if not isinstance(raw_data, dict):
                return False
            
            # Check required fields
            required_fields = ['symbol', 'timestamp', 'open', 'high', 'low', 'last', 'bid', 'ask', 'volume']
            for field in required_fields:
                if field not in raw_data:
                    return False
            
            # Validate symbol
            symbol = raw_data['symbol']
            if not isinstance(symbol, str) or len(symbol) == 0 or len(symbol) > 50:
                return False
            
            # Validate timestamp
            timestamp = raw_data['timestamp']
            if not isinstance(timestamp, datetime):
                return False
            
            # Validate price fields
            price_fields = ['open', 'high', 'low', 'last', 'bid', 'ask']
            for field in price_fields:
                value = raw_data[field]
                if not isinstance(value, Decimal) or value <= 0:
                    return False
            
            # Validate volume
            volume = raw_data['volume']
            if not isinstance(volume, Decimal) or volume < 0:
                return False
            
            # Validate price relationships
            open_price = raw_data['open']
            high_price = raw_data['high']
            low_price = raw_data['low']
            close_price = raw_data['last']
            bid_price = raw_data['bid']
            ask_price = raw_data['ask']
            
            # OHLC validation: high >= max(open, close) and low <= min(open, close)
            if high_price < max(open_price, close_price):
                return False
            if low_price > min(open_price, close_price):
                return False
            
            # Bid/Ask validation: bid < ask
            if bid_price >= ask_price:
                return False
            
            # Price reasonableness: all prices should be within reasonable bounds
            # Allow very small prices (like 1E-8) but reject unreasonably large ones
            max_price = Decimal('1000000000')  # 1 billion
            min_price = Decimal('0.000000001')  # 1E-9 (smaller than 1E-8 to handle calculations)
            
            for field in price_fields:
                price = raw_data[field]
                if price < min_price or price > max_price:
                    return False
            
            # Note: Extra/unexpected fields are allowed and processed gracefully
            # This supports API responses that may include additional metadata
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating market data: {e}")
            return False
    
    def _update_indicators(self, symbol: str) -> None:
        """Update technical indicators for a symbol."""
        try:
            data_points = list(self._price_data[symbol])
            if len(data_points) < 2:
                return
            
            # Extract price series
            closes = [float(point['last']) for point in data_points]
            highs = [float(point['high']) for point in data_points]
            lows = [float(point['low']) for point in data_points]
            
            # Calculate RSI
            if len(closes) >= self._indicator_params['RSI']['period']:
                rsi = self._calculate_rsi(closes, self._indicator_params['RSI']['period'])
                self._indicators[symbol]['RSI'] = rsi
            
            # Calculate Simple Moving Averages
            for indicator in ['SMA_20', 'SMA_50']:
                period = self._indicator_params[indicator]['period']
                if len(closes) >= period:
                    sma = self._calculate_sma(closes, period)
                    self._indicators[symbol][indicator] = sma
            
            # Calculate Exponential Moving Averages
            for indicator in ['EMA_12', 'EMA_26']:
                period = self._indicator_params[indicator]['period']
                if len(closes) >= period:
                    ema = self._calculate_ema(closes, period)
                    self._indicators[symbol][indicator] = ema
            
            # Calculate MACD
            if len(closes) >= self._indicator_params['MACD']['slow']:
                macd_line, signal_line, histogram = self._calculate_macd(closes)
                self._indicators[symbol]['MACD'] = macd_line
                self._indicators[symbol]['MACD_Signal'] = signal_line
                self._indicators[symbol]['MACD_Histogram'] = histogram
            
        except Exception as e:
            logger.error(f"Error updating indicators for {symbol}: {e}")
    
    def _calculate_rsi(self, prices: List[float], period: int) -> float:
        """Calculate Relative Strength Index using Wilder's smoothing method."""
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI for insufficient data
        
        # Calculate price changes
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # Separate gains and losses
        gains = [max(delta, 0) for delta in deltas]
        losses = [max(-delta, 0) for delta in deltas]
        
        # Handle edge case: no price changes (constant prices)
        if all(gain == 0 for gain in gains) and all(loss == 0 for loss in losses):
            return 50.0  # Neutral RSI for constant prices
        
        # Calculate initial averages using simple average for first period
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # Apply Wilder's smoothing for remaining periods
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        # Handle edge case: no losses
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        
        # Calculate RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def _calculate_sma(self, prices: List[float], period: int) -> float:
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        
        return round(sum(prices[-period:]) / period, 2)
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        
        multiplier = 2 / (period + 1)
        ema = prices[0]  # Start with first price
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return round(ema, 2)
    
    def _calculate_macd(self, prices: List[float]) -> tuple[float, float, float]:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        params = self._indicator_params['MACD']
        
        if len(prices) < params['slow']:
            return 0.0, 0.0, 0.0
        
        # Calculate EMAs
        ema_fast = self._calculate_ema(prices, params['fast'])
        ema_slow = self._calculate_ema(prices, params['slow'])
        
        # MACD line
        macd_line = ema_fast - ema_slow
        
        # For signal line, we need historical MACD values
        # Simplified calculation for now
        signal_line = macd_line * 0.9  # Approximation
        
        # Histogram
        histogram = macd_line - signal_line
        
        return round(macd_line, 4), round(signal_line, 4), round(histogram, 4)
    
    def stop(self) -> None:
        """Stop the data handler and cleanup resources."""
        self._running = False
        
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=5)
        
        # Close websocket connections
        for connection in self._websocket_connections.values():
            try:
                if hasattr(connection, 'close'):
                    connection.close()
            except Exception as e:
                logger.error(f"Error closing websocket connection: {e}")
        
        logger.info("Data handler stopped")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.stop()