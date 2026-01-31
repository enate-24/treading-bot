#!/usr/bin/env python3
"""Isolated test to debug signal generation."""

import sys
from datetime import datetime
from decimal import Decimal

# Add the project root to the path
sys.path.insert(0, '.')

from trading_bot.signal_generator import SignalGenerator
from trading_bot.strategies.scalping_strategy import ScalpingStrategy
from trading_bot.models import MarketData, OHLCV


def test_isolated_signal():
    """Test signal generation in isolation."""
    print("=== Isolated Signal Generation Test ===")
    
    # Create strategy with exact test parameters
    strategy_params = {
        'rsi_oversold': 30.0,
        'rsi_overbought': 70.0,
        'volume_threshold': 1.5,
        'min_confidence': 0.1,
        'lookback_periods': 5
    }
    
    # Create signal generator and strategy
    signal_generator = SignalGenerator()
    strategy = ScalpingStrategy(strategy_params)
    signal_generator.set_strategy(strategy)
    
    print(f"Strategy parameters: {strategy.get_parameters()}")
    print(f"Initial strategy state: {strategy._state}")
    
    # Populate volume history exactly like the test
    symbol = '000'
    base_price = Decimal('1000')
    volume = Decimal('100000')
    volume_multiplier = 2.0
    
    for i in range(6):
        historical_data = MarketData(
            symbol=symbol,
            timestamp=datetime(2024, 1, 1, 12, i, 0),
            ohlcv=OHLCV(
                open=base_price,
                high=base_price * Decimal('1.01'),
                low=base_price * Decimal('0.99'),
                close=base_price,
                volume=volume / Decimal(str(volume_multiplier))  # Lower volume for baseline
            ),
            indicators={
                'RSI': 50.0,  # Neutral RSI for baseline
                'SMA_20': float(base_price),
                'SMA_50': float(base_price)
            }
        )
        print(f"Processing historical data {i}: volume={historical_data.ohlcv.volume}")
        signal = signal_generator.analyze_market_data(historical_data)
        print(f"  Historical signal: {signal}")
        print(f"  Strategy state: volume_history={len(strategy._state['volume_history'])}, avg_volume={strategy._state.get('avg_volume')}")
    
    print(f"Final strategy state: {strategy._state}")
    
    # Create signal market data exactly like the test
    signal_market_data = MarketData(
        symbol=symbol,
        timestamp=datetime(2024, 1, 1, 12, 10, 0),
        ohlcv=OHLCV(
            open=base_price,
            high=base_price * Decimal('1.01'),
            low=base_price * Decimal('0.99'),
            close=base_price,
            volume=volume  # High volume (spike)
        ),
        indicators={
            'RSI': 15.0,  # Oversold condition
            'SMA_20': float(base_price),
            'SMA_50': float(base_price)
        }
    )
    
    print(f"\nSignal market data: RSI={signal_market_data.indicators['RSI']}, volume={signal_market_data.ohlcv.volume}")
    
    # Generate signal
    signal = signal_generator.analyze_market_data(signal_market_data)
    
    print(f"\nGenerated signal: {signal}")
    if signal:
        print(f"  Direction: {signal.direction}")
        print(f"  Strength: {signal.strength}")
        print(f"  Confidence: {signal.confidence}")
        print(f"  Strategy: {signal.strategy}")
        print(f"  Metadata: {signal.metadata}")
        print(f"  Metadata type: {type(signal.metadata)}")
        print(f"  Metadata keys: {list(signal.metadata.keys())}")
        
        # Check each expected field
        expected_fields = ['rsi', 'volume_spike', 'avg_volume', 'current_volume', 'profit_target', 'stop_loss', 'entry_price']
        for field in expected_fields:
            if field in signal.metadata:
                print(f"    ✓ {field}: {signal.metadata[field]}")
            else:
                print(f"    ✗ {field}: MISSING")
    else:
        print("  No signal generated!")
    
    # Test the strategy directly
    print(f"\n=== Testing strategy directly ===")
    direct_signal = strategy.analyze(signal_market_data)
    print(f"Direct signal: {direct_signal}")
    if direct_signal:
        print(f"  Direct metadata: {direct_signal.metadata}")


if __name__ == "__main__":
    test_isolated_signal()