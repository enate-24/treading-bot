#!/usr/bin/env python3

import sys
sys.path.append('.')

from decimal import Decimal
from datetime import datetime
from trading_bot.strategies.scalping_strategy import ScalpingStrategy
from trading_bot.signal_generator import SignalGenerator
from trading_bot.models import MarketData, OHLCV

def test_scalping_signal():
    # Create strategy with specific parameters to ensure signal generation
    strategy_params = {
        'rsi_oversold': 30.0,
        'rsi_overbought': 70.0,
        'volume_threshold': 1.5,
        'min_confidence': 0.1,  # Low threshold to ensure signals are generated
        'lookback_periods': 5
    }
    
    # Create signal generator and strategy
    signal_generator = SignalGenerator()
    strategy = ScalpingStrategy(strategy_params)
    signal_generator.set_strategy(strategy)
    
    # Test parameters
    symbol = 'BTC/USD'
    base_price = Decimal('50000.00')
    volume = Decimal('10000.00')
    rsi_oversold = 25.0
    volume_multiplier = 3.0
    
    # First, populate volume history to establish baseline
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
        signal_generator.analyze_market_data(historical_data)
    
    # Now create market data with signal conditions (oversold RSI + volume spike)
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
    
    # Generate signal
    signal = signal_generator.analyze_market_data(signal_market_data)
    
    print(f"Generated signal: {signal}")
    if signal:
        print(f"Signal metadata: {signal.metadata}")
        print(f"Has volume_spike: {'volume_spike' in signal.metadata}")
        if 'volume_spike' in signal.metadata:
            print(f"Volume spike value: {signal.metadata['volume_spike']}")
    else:
        print("No signal generated")

if __name__ == "__main__":
    test_scalping_signal()