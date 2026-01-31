#!/usr/bin/env python3

import sys
sys.path.append('.')

from decimal import Decimal
from datetime import datetime
from trading_bot.strategies.swing_trading_strategy import SwingTradingStrategy
from trading_bot.signal_generator import SignalGenerator
from trading_bot.models import MarketData, OHLCV

def test_swing_signal():
    # Create strategy with specific parameters to ensure signal generation
    strategy_params = {
        'fast_ma_period': 20,
        'slow_ma_period': 50,
        'min_confidence': 0.1,  # Low threshold to ensure signals are generated
        'crossover_threshold': 0.001,  # 0.1% minimum crossover
        'volume_confirmation': False  # Disable volume confirmation for this test
    }
    
    # Create signal generator and strategy
    signal_generator = SignalGenerator()
    strategy = SwingTradingStrategy(strategy_params)
    signal_generator.set_strategy(strategy)
    
    # Test parameters
    symbol = 'BTC/USD'
    base_price = Decimal('50000.00')
    volume = Decimal('10000.00')
    fast_ma_multiplier = 1.05  # Fast MA above slow MA
    slow_ma_multiplier = 0.95  # Slow MA below fast MA
    
    # Calculate MA values
    fast_ma_value = float(base_price * Decimal(str(fast_ma_multiplier)))
    slow_ma_value = float(base_price * Decimal(str(slow_ma_multiplier)))
    
    print(f"Fast MA: {fast_ma_value}, Slow MA: {slow_ma_value}")
    
    # First, establish a bearish state (fast MA below slow MA)
    for i in range(3):
        pre_crossover_data = MarketData(
            symbol=symbol,
            timestamp=datetime(2024, 1, 1, 12, i, 0),
            ohlcv=OHLCV(
                open=base_price,
                high=base_price * Decimal('1.01'),
                low=base_price * Decimal('0.99'),
                close=base_price,
                volume=volume
            ),
            indicators={
                'RSI': 50.0,
                'SMA_20': slow_ma_value - 1000,  # Fast MA below slow MA
                'SMA_50': slow_ma_value
            }
        )
        signal_generator.analyze_market_data(pre_crossover_data)
    
    # Now create the golden cross (fast MA crosses above slow MA)
    crossover_market_data = MarketData(
        symbol=symbol,
        timestamp=datetime(2024, 1, 1, 12, 10, 0),
        ohlcv=OHLCV(
            open=base_price,
            high=base_price * Decimal('1.01'),
            low=base_price * Decimal('0.99'),
            close=base_price,
            volume=volume
        ),
        indicators={
            'RSI': 50.0,
            'SMA_20': fast_ma_value,   # Fast MA now above slow MA
            'SMA_50': slow_ma_value    # Slow MA
        }
    )
    
    # Generate signal
    signal = signal_generator.analyze_market_data(crossover_market_data)
    
    print(f"Generated signal: {signal}")
    if signal:
        print(f"Signal metadata: {signal.metadata}")
        print(f"Has crossover_type: {'crossover_type' in signal.metadata}")
        if 'crossover_type' in signal.metadata:
            print(f"Crossover type: {signal.metadata['crossover_type']}")
    else:
        print("No signal generated")

if __name__ == "__main__":
    test_swing_signal()