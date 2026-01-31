#!/usr/bin/env python3
"""Debug script to investigate scalping strategy signal generation."""

import sys
from datetime import datetime
from decimal import Decimal

# Add the project root to the path
sys.path.insert(0, '.')

from trading_bot.signal_generator import SignalGenerator
from trading_bot.strategies.scalping_strategy import ScalpingStrategy
from trading_bot.models import MarketData, OHLCV


def debug_scalping_signal():
    """Debug the failing scalping signal generation."""
    print("=== Debugging Scalping Strategy Signal Generation ===")
    
    # Use the exact parameters from the failing test
    symbol = '000'
    base_price = Decimal('1000')
    volume = Decimal('100000')
    rsi_oversold = 15.0
    rsi_overbought = 65.0
    volume_multiplier = 2.0
    
    print(f"Test parameters:")
    print(f"  Symbol: {symbol}")
    print(f"  Base price: {base_price}")
    print(f"  Volume: {volume}")
    print(f"  RSI oversold: {rsi_oversold}")
    print(f"  RSI overbought: {rsi_overbought}")
    print(f"  Volume multiplier: {volume_multiplier}")
    
    # Create strategy with test parameters
    strategy_params = {
        'rsi_oversold': 30.0,
        'rsi_overbought': 70.0,
        'volume_threshold': 1.5,
        'min_confidence': 0.1,  # Low threshold to ensure signals are generated
        'lookback_periods': 5
    }
    
    print(f"\nStrategy parameters: {strategy_params}")
    
    # Create signal generator and strategy
    signal_generator = SignalGenerator()
    strategy = ScalpingStrategy(strategy_params)
    signal_generator.set_strategy(strategy)
    
    print(f"\nStrategy state before historical data: {strategy._state}")
    
    # First, populate volume history to establish baseline
    print("\n=== Populating volume history ===")
    for i in range(6):  # Need at least 5 periods for volume average
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
        print(f"  Period {i}: volume={historical_data.ohlcv.volume}, RSI={historical_data.indicators['RSI']}")
        
        # Call strategy analyze directly to debug
        print(f"    Calling strategy.analyze directly...")
        direct_signal = strategy.analyze(historical_data)
        print(f"    Direct signal: {direct_signal}")
        print(f"    Strategy state after direct call: volume_history length={len(strategy._state['volume_history'])}, avg_volume={strategy._state.get('avg_volume')}")
        
        # Also call through signal generator
        signal = signal_generator.analyze_market_data(historical_data)
        print(f"    Signal through generator: {signal}")
        print(f"    Strategy state after generator call: volume_history length={len(strategy._state['volume_history'])}, avg_volume={strategy._state.get('avg_volume')}")
    
    print(f"\nStrategy state after historical data: {strategy._state}")
    
    # Now create market data with signal conditions (oversold RSI + volume spike)
    print("\n=== Creating signal market data ===")
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
            'RSI': rsi_oversold,  # Oversold condition
            'SMA_20': float(base_price),
            'SMA_50': float(base_price)
        }
    )
    
    print(f"Signal market data:")
    print(f"  Volume: {signal_market_data.ohlcv.volume}")
    print(f"  RSI: {signal_market_data.indicators['RSI']}")
    print(f"  Expected volume spike: {float(volume) / (float(volume) / volume_multiplier)} = {volume_multiplier}")
    
    # Generate signal
    print("\n=== Generating signal ===")
    signal = signal_generator.analyze_market_data(signal_market_data)
    
    print(f"Generated signal: {signal}")
    if signal:
        print(f"  Direction: {signal.direction}")
        print(f"  Strength: {signal.strength}")
        print(f"  Confidence: {signal.confidence}")
        print(f"  Strategy: {signal.strategy}")
        print(f"  Metadata: {signal.metadata}")
        print(f"  Metadata keys: {list(signal.metadata.keys())}")
        
        # Check specific metadata fields
        if 'rsi' in signal.metadata:
            print(f"    RSI in metadata: {signal.metadata['rsi']}")
        if 'volume_spike' in signal.metadata:
            print(f"    Volume spike in metadata: {signal.metadata['volume_spike']}")
        else:
            print("    ERROR: volume_spike NOT in metadata!")
    else:
        print("  No signal generated!")
        
        # Debug why no signal was generated
        print("\n=== Debugging why no signal was generated ===")
        current_volume = float(signal_market_data.ohlcv.volume)
        avg_volume = strategy._state.get('avg_volume')
        if avg_volume:
            volume_spike = current_volume / avg_volume
            print(f"  Current volume: {current_volume}")
            print(f"  Average volume: {avg_volume}")
            print(f"  Volume spike: {volume_spike}")
            print(f"  Volume threshold: {strategy_params['volume_threshold']}")
            print(f"  Volume condition met: {volume_spike >= strategy_params['volume_threshold']}")
        
        rsi = signal_market_data.indicators.get('RSI')
        print(f"  RSI: {rsi}")
        print(f"  RSI oversold threshold: {strategy_params['rsi_oversold']}")
        print(f"  RSI oversold condition: {rsi <= strategy_params['rsi_oversold']}")
        print(f"  RSI overbought threshold: {strategy_params['rsi_overbought']}")
        print(f"  RSI overbought condition: {rsi >= strategy_params['rsi_overbought']}")
        
        print(f"  Has sufficient data: {strategy._has_sufficient_data()}")
        print(f"  Last signal time: {strategy._state.get('last_signal_time')}")


if __name__ == "__main__":
    debug_scalping_signal()