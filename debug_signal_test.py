#!/usr/bin/env python3
"""Debug script for signal generation testing."""

from trading_bot.signal_generator import SignalGenerator
from trading_bot.strategies.scalping_strategy import ScalpingStrategy
from trading_bot.models import MarketData, OHLCV, SignalDirection
from datetime import datetime
from decimal import Decimal

def test_basic_signal_generation():
    """Test basic signal generation functionality."""
    print("Testing basic signal generation...")
    
    # Create signal generator and strategy
    signal_generator = SignalGenerator()
    strategy = ScalpingStrategy({
        'rsi_oversold': 30.0, 
        'rsi_overbought': 70.0, 
        'volume_threshold': 1.5, 
        'min_confidence': 0.1,
        'lookback_periods': 5
    })
    signal_generator.set_strategy(strategy)
    
    # First, populate volume history to establish baseline
    print("Populating volume history...")
    for i in range(6):
        historical_data = MarketData(
            symbol='BTC/USD',
            timestamp=datetime(2024, 1, 1, 12, i, 0),
            ohlcv=OHLCV(
                open=Decimal('50000'),
                high=Decimal('50500'),
                low=Decimal('49500'),
                close=Decimal('50000'),
                volume=Decimal('1000')  # Low volume for baseline
            ),
            indicators={
                'RSI': 50.0,  # Neutral RSI
                'SMA_20': 50000.0,
                'SMA_50': 50000.0
            }
        )
        signal = signal_generator.analyze_market_data(historical_data)
        print(f"Historical data {i}: signal = {signal}")
    
    # Now test with oversold condition + volume spike
    print("Testing oversold condition with volume spike...")
    signal_market_data = MarketData(
        symbol='BTC/USD',
        timestamp=datetime(2024, 1, 1, 12, 10, 0),
        ohlcv=OHLCV(
            open=Decimal('50000'),
            high=Decimal('50500'),
            low=Decimal('49500'),
            close=Decimal('50000'),
            volume=Decimal('2000')  # High volume (2x baseline)
        ),
        indicators={
            'RSI': 25.0,  # Oversold
            'SMA_20': 50000.0,
            'SMA_50': 50000.0
        }
    )
    
    signal = signal_generator.analyze_market_data(signal_market_data)
    print(f"Oversold signal: {signal}")
    
    if signal:
        print(f"Direction: {signal.direction}")
        print(f"Strength: {signal.strength}")
        print(f"Confidence: {signal.confidence}")
        print(f"Metadata: {signal.metadata}")
        print(f"Strategy state: {strategy._state}")
    
    return signal

if __name__ == "__main__":
    test_basic_signal_generation()