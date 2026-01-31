#!/usr/bin/env python3
"""Debug script to investigate state update issues."""

import sys
from datetime import datetime
from decimal import Decimal

# Add the project root to the path
sys.path.insert(0, '.')

from trading_bot.strategies.scalping_strategy import ScalpingStrategy
from trading_bot.models import MarketData, OHLCV


def debug_state_update():
    """Debug the state update issue."""
    print("=== Debugging State Update ===")
    
    # Create strategy
    strategy_params = {
        'rsi_oversold': 30.0,
        'rsi_overbought': 70.0,
        'volume_threshold': 1.5,
        'min_confidence': 0.1,
        'lookback_periods': 5
    }
    
    strategy = ScalpingStrategy(strategy_params)
    print(f"Initial state: {strategy._state}")
    
    # Create test market data
    base_price = Decimal('1000')
    volume = Decimal('50000')
    
    market_data = MarketData(
        symbol='TEST',
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        ohlcv=OHLCV(
            open=base_price,
            high=base_price * Decimal('1.01'),
            low=base_price * Decimal('0.99'),
            close=base_price,
            volume=volume
        ),
        indicators={
            'RSI': 50.0,
            'SMA_20': float(base_price),
            'SMA_50': float(base_price)
        }
    )
    
    print(f"\nTest market data:")
    print(f"  Volume: {market_data.ohlcv.volume}")
    print(f"  RSI: {market_data.indicators['RSI']}")
    
    # Test _update_state directly
    print(f"\n=== Testing _update_state directly ===")
    try:
        rsi = market_data.indicators.get('RSI')
        current_volume = float(market_data.ohlcv.volume)
        current_price = float(market_data.ohlcv.close)
        
        print(f"Calling _update_state with:")
        print(f"  rsi: {rsi}")
        print(f"  volume: {current_volume}")
        print(f"  price: {current_price}")
        
        strategy._update_state(market_data, rsi, current_volume, current_price)
        print(f"State after _update_state: {strategy._state}")
        
    except Exception as e:
        print(f"Exception in _update_state: {e}")
        import traceback
        traceback.print_exc()
    
    # Test analyze method
    print(f"\n=== Testing analyze method ===")
    try:
        signal = strategy.analyze(market_data)
        print(f"Signal from analyze: {signal}")
        print(f"State after analyze: {strategy._state}")
        
    except Exception as e:
        print(f"Exception in analyze: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    debug_state_update()