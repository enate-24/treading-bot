#!/usr/bin/env python3
"""Simple debug script to test signal generation."""

import sys
from datetime import datetime
from decimal import Decimal

# Add the project root to the path
sys.path.insert(0, '.')

from trading_bot.strategies.scalping_strategy import ScalpingStrategy
from trading_bot.models import MarketData, OHLCV


def test_simple_signal():
    """Test simple signal generation."""
    print("=== Simple Signal Generation Test ===")
    
    # Create strategy with simple parameters
    strategy = ScalpingStrategy({
        'rsi_oversold': 30.0,
        'rsi_overbought': 70.0,
        'volume_threshold': 1.5,
        'min_confidence': 0.1,
        'lookback_periods': 5
    })
    
    print(f"Initial strategy state: {strategy._state}")
    
    # Manually populate volume history
    strategy._state['volume_history'] = [1000.0, 1000.0, 1000.0, 1000.0, 1000.0]
    strategy._state['avg_volume'] = 1000.0
    
    print(f"After manual setup: {strategy._state}")
    
    # Create market data with clear signal conditions
    market_data = MarketData(
        symbol='TEST',
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        ohlcv=OHLCV(
            open=Decimal('100'),
            high=Decimal('101'),
            low=Decimal('99'),
            close=Decimal('100'),
            volume=Decimal('2000')  # 2x the average volume
        ),
        indicators={
            'RSI': 25.0,  # Clearly oversold
            'SMA_20': 100.0,
            'SMA_50': 100.0
        }
    )
    
    print(f"Market data: RSI={market_data.indicators['RSI']}, volume={market_data.ohlcv.volume}")
    
    # Generate signal
    signal = strategy.analyze(market_data)
    
    print(f"Generated signal: {signal}")
    if signal:
        print(f"  Metadata: {signal.metadata}")
        print(f"  Metadata keys: {list(signal.metadata.keys())}")
    
    # Test volume spike calculation directly
    volume_spike = strategy._calculate_volume_spike(2000.0)
    print(f"Volume spike calculation: {volume_spike}")
    
    # Test conditions directly
    rsi = 25.0
    rsi_oversold = rsi <= strategy.parameters['rsi_oversold']
    volume_condition = volume_spike >= strategy.parameters['volume_threshold']
    
    print(f"RSI oversold condition: {rsi_oversold} (RSI {rsi} <= {strategy.parameters['rsi_oversold']})")
    print(f"Volume condition: {volume_condition} (spike {volume_spike} >= {strategy.parameters['volume_threshold']})")
    
    # Test signal generation directly
    print("\n=== Testing _generate_signal directly ===")
    direct_signal = strategy._generate_signal(market_data, rsi, volume_spike)
    print(f"Direct signal: {direct_signal}")
    if direct_signal:
        print(f"  Direct metadata: {direct_signal.metadata}")


if __name__ == "__main__":
    test_simple_signal()