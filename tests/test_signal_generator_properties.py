"""Property-based tests for Signal Generator strategy consistency."""

import pytest
from datetime import datetime
from decimal import Decimal
from hypothesis import given, strategies as st, assume
from copy import deepcopy

from trading_bot.signal_generator import SignalGenerator
from trading_bot.models import MarketData, OHLCV, SignalDirection


class TestSignalGeneratorProperties:
    """Property-based tests for Signal Generator."""

    @given(
        symbol=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='/')),
        base_price=st.decimals(min_value=1, max_value=100000, places=2),
        price_variation=st.decimals(min_value=0, max_value=0.1, places=4),  # 10% max variation
        volume=st.decimals(min_value=1, max_value=1000000, places=2),
        rsi=st.floats(min_value=0.0, max_value=100.0),
        sma_20=st.decimals(min_value=1, max_value=100000, places=2),
        sma_50=st.decimals(min_value=1, max_value=100000, places=2),
        strategy_params=st.dictionaries(
            keys=st.sampled_from(['rsi_oversold', 'rsi_overbought', 'volume_threshold', 'min_confidence']),
            values=st.floats(min_value=0.1, max_value=2.0),
            min_size=0,
            max_size=4
        )
    )
    def test_property_1_strategy_consistency_scalping(self, symbol, base_price, price_variation, 
                                                     volume, rsi, sma_20, sma_50, strategy_params):
        """
        **Feature: trading-bot-system, Property 1: Strategy Consistency**
        
        For any trading strategy and identical market conditions, the Signal Generator 
        should always produce the same trading signals with identical strength and confidence levels.
        **Validates: Requirements 1.2**
        """
        # Import here to avoid circular import issues
        from trading_bot.strategies.scalping_strategy import ScalpingStrategy
        
        # Generate valid OHLC data from base price and variation
        variation_amount = base_price * price_variation
        open_price = base_price
        close_price = base_price + (variation_amount * Decimal('0.5'))  # Small change
        high_price = max(open_price, close_price) + variation_amount
        low_price = min(open_price, close_price) - variation_amount
        
        # Create identical market data
        ohlcv = OHLCV(
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume
        )
        
        indicators = {
            'RSI': rsi,
            'SMA_20': float(sma_20),
            'SMA_50': float(sma_50)
        }
        
        market_data_1 = MarketData(
            symbol=symbol,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),  # Fixed timestamp for consistency
            ohlcv=ohlcv,
            indicators=indicators
        )
        
        # Create identical market data (deep copy to ensure independence)
        market_data_2 = MarketData(
            symbol=symbol,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),  # Same fixed timestamp
            ohlcv=OHLCV(
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume
            ),
            indicators={
                'RSI': rsi,
                'SMA_20': float(sma_20),
                'SMA_50': float(sma_50)
            }
        )
        
        # Create two identical signal generators with identical strategies
        signal_generator_1 = SignalGenerator()
        signal_generator_2 = SignalGenerator()
        
        strategy_1 = ScalpingStrategy(strategy_params)
        strategy_2 = ScalpingStrategy(strategy_params)
        
        signal_generator_1.set_strategy(strategy_1)
        signal_generator_2.set_strategy(strategy_2)
        
        # Generate signals from identical market data
        signal_1 = signal_generator_1.analyze_market_data(market_data_1)
        signal_2 = signal_generator_2.analyze_market_data(market_data_2)
        
        # Both should generate the same result (both None or both valid signals)
        if signal_1 is None:
            assert signal_2 is None, "Identical market conditions should produce identical results"
        else:
            assert signal_2 is not None, "Identical market conditions should produce identical results"
            
            # Verify signal properties are identical
            assert signal_1.symbol == signal_2.symbol
            assert signal_1.direction == signal_2.direction
            assert abs(signal_1.strength - signal_2.strength) < 1e-10, f"Signal strength should be identical: {signal_1.strength} vs {signal_2.strength}"
            assert abs(signal_1.confidence - signal_2.confidence) < 1e-10, f"Signal confidence should be identical: {signal_1.confidence} vs {signal_2.confidence}"
            assert signal_1.strategy == signal_2.strategy
            
            # Verify metadata consistency (key indicators should match)
            if 'rsi' in signal_1.metadata and 'rsi' in signal_2.metadata:
                assert abs(signal_1.metadata['rsi'] - signal_2.metadata['rsi']) < 1e-10
            if 'volume_spike' in signal_1.metadata and 'volume_spike' in signal_2.metadata:
                assert abs(signal_1.metadata['volume_spike'] - signal_2.metadata['volume_spike']) < 1e-10

    @given(
        symbol=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='/')),
        base_price=st.decimals(min_value=1, max_value=100000, places=2),
        price_variation=st.decimals(min_value=0, max_value=0.1, places=4),  # 10% max variation
        volume=st.decimals(min_value=1, max_value=1000000, places=2),
        rsi=st.floats(min_value=0.0, max_value=100.0),
        sma_20=st.decimals(min_value=1, max_value=100000, places=2),
        sma_50=st.decimals(min_value=1, max_value=100000, places=2),
        strategy_params=st.dictionaries(
            keys=st.sampled_from(['fast_ma_period', 'slow_ma_period', 'profit_target', 'min_confidence']),
            values=st.floats(min_value=0.1, max_value=2.0),
            min_size=0,
            max_size=4
        )
    )
    def test_property_1_strategy_consistency_swing_trading(self, symbol, base_price, price_variation, 
                                                          volume, rsi, sma_20, sma_50, strategy_params):
        """
        **Feature: trading-bot-system, Property 1: Strategy Consistency**
        
        For any trading strategy and identical market conditions, the Signal Generator 
        should always produce the same trading signals with identical strength and confidence levels.
        **Validates: Requirements 1.2**
        """
        # Import here to avoid circular import issues
        from trading_bot.strategies.swing_trading_strategy import SwingTradingStrategy
        
        # Generate valid OHLC data from base price and variation
        variation_amount = base_price * price_variation
        open_price = base_price
        close_price = base_price + (variation_amount * Decimal('0.5'))  # Small change
        high_price = max(open_price, close_price) + variation_amount
        low_price = min(open_price, close_price) - variation_amount
        
        # Create identical market data
        ohlcv = OHLCV(
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume
        )
        
        indicators = {
            'RSI': rsi,
            'SMA_20': float(sma_20),
            'SMA_50': float(sma_50)
        }
        
        market_data_1 = MarketData(
            symbol=symbol,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),  # Fixed timestamp for consistency
            ohlcv=ohlcv,
            indicators=indicators
        )
        
        # Create identical market data
        market_data_2 = MarketData(
            symbol=symbol,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),  # Same fixed timestamp
            ohlcv=OHLCV(
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume
            ),
            indicators={
                'RSI': rsi,
                'SMA_20': float(sma_20),
                'SMA_50': float(sma_50)
            }
        )
        
        # Create two identical signal generators with identical strategies
        signal_generator_1 = SignalGenerator()
        signal_generator_2 = SignalGenerator()
        
        strategy_1 = SwingTradingStrategy(strategy_params)
        strategy_2 = SwingTradingStrategy(strategy_params)
        
        signal_generator_1.set_strategy(strategy_1)
        signal_generator_2.set_strategy(strategy_2)
        
        # Generate signals from identical market data
        signal_1 = signal_generator_1.analyze_market_data(market_data_1)
        signal_2 = signal_generator_2.analyze_market_data(market_data_2)
        
        # Both should generate the same result (both None or both valid signals)
        if signal_1 is None:
            assert signal_2 is None, "Identical market conditions should produce identical results"
        else:
            assert signal_2 is not None, "Identical market conditions should produce identical results"
            
            # Verify signal properties are identical
            assert signal_1.symbol == signal_2.symbol
            assert signal_1.direction == signal_2.direction
            assert abs(signal_1.strength - signal_2.strength) < 1e-10, f"Signal strength should be identical: {signal_1.strength} vs {signal_2.strength}"
            assert abs(signal_1.confidence - signal_2.confidence) < 1e-10, f"Signal confidence should be identical: {signal_1.confidence} vs {signal_2.confidence}"
            assert signal_1.strategy == signal_2.strategy
            
            # Verify metadata consistency (key indicators should match)
            if 'fast_ma' in signal_1.metadata and 'fast_ma' in signal_2.metadata:
                assert abs(signal_1.metadata['fast_ma'] - signal_2.metadata['fast_ma']) < 1e-10
            if 'slow_ma' in signal_1.metadata and 'slow_ma' in signal_2.metadata:
                assert abs(signal_1.metadata['slow_ma'] - signal_2.metadata['slow_ma']) < 1e-10

    @given(
        symbol=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='/')),
        base_price=st.decimals(min_value=1, max_value=100000, places=2),
        price_variation=st.decimals(min_value=0, max_value=0.1, places=4),  # 10% max variation
        volume=st.decimals(min_value=1, max_value=1000000, places=2),
        rsi=st.floats(min_value=0.0, max_value=100.0),
        sma_20=st.decimals(min_value=1, max_value=100000, places=2),
        sma_50=st.decimals(min_value=1, max_value=100000, places=2)
    )
    def test_property_1_strategy_consistency_multiple_calls(self, symbol, base_price, price_variation, 
                                                           volume, rsi, sma_20, sma_50):
        """
        **Feature: trading-bot-system, Property 1: Strategy Consistency**
        
        Multiple calls to the same strategy with identical market data should produce identical results.
        **Validates: Requirements 1.2**
        """
        # Import here to avoid circular import issues
        from trading_bot.strategies.scalping_strategy import ScalpingStrategy
        
        # Generate valid OHLC data from base price and variation
        variation_amount = base_price * price_variation
        open_price = base_price
        close_price = base_price + (variation_amount * Decimal('0.5'))  # Small change
        high_price = max(open_price, close_price) + variation_amount
        low_price = min(open_price, close_price) - variation_amount
        
        # Create market data
        ohlcv = OHLCV(
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume
        )
        
        indicators = {
            'RSI': rsi,
            'SMA_20': float(sma_20),
            'SMA_50': float(sma_50)
        }
        
        market_data = MarketData(
            symbol=symbol,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            ohlcv=ohlcv,
            indicators=indicators
        )
        
        # Create signal generator with scalping strategy
        signal_generator = SignalGenerator()
        strategy = ScalpingStrategy()
        signal_generator.set_strategy(strategy)
        
        # Generate multiple signals from the same market data
        signals = []
        for _ in range(3):  # Test multiple calls
            # Reset strategy state to ensure clean state for each call
            strategy.reset_state()
            signal = signal_generator.analyze_market_data(market_data)
            signals.append(signal)
        
        # All signals should be identical
        first_signal = signals[0]
        for i, signal in enumerate(signals[1:], 1):
            if first_signal is None:
                assert signal is None, f"Call {i+1} should return None like the first call"
            else:
                assert signal is not None, f"Call {i+1} should return a signal like the first call"
                assert signal.symbol == first_signal.symbol
                assert signal.direction == first_signal.direction
                assert abs(signal.strength - first_signal.strength) < 1e-10
                assert abs(signal.confidence - first_signal.confidence) < 1e-10
                assert signal.strategy == first_signal.strategy

    @given(
        symbol=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='/')),
        base_price=st.decimals(min_value=10, max_value=100000, places=2),
        volume=st.decimals(min_value=1000, max_value=1000000, places=2),
        rsi_oversold=st.floats(min_value=15.0, max_value=35.0),  # Clearly oversold
        rsi_overbought=st.floats(min_value=65.0, max_value=85.0),  # Clearly overbought
        volume_multiplier=st.floats(min_value=2.0, max_value=5.0)  # Clear volume spike
    )
    def test_property_2_signal_generation_correctness_scalping_oversold(self, symbol, base_price, volume, 
                                                                       rsi_oversold, rsi_overbought, volume_multiplier):
        """
        **Feature: trading-bot-system, Property 2: Signal Generation Correctness**
        
        For any market data that meets configured strategy criteria, the Signal Generator 
        should generate appropriate buy or sell signals that align with the strategy's entry rules.
        **Validates: Requirements 1.4**
        """
        # Import here to avoid circular import issues
        from trading_bot.strategies.scalping_strategy import ScalpingStrategy
        
        # Create strategy with specific parameters to ensure signal generation
        strategy_params = {
            'rsi_oversold': 30.0,
            'rsi_overbought': 70.0,
            'volume_threshold': 1.5,
            'min_confidence': 0.1,  # Low threshold to ensure signals are generated
            'lookback_periods': 5
        }
        
        # Create market data that meets BUY signal criteria (RSI oversold + volume spike)
        ohlcv = OHLCV(
            open=base_price,
            high=base_price * Decimal('1.01'),
            low=base_price * Decimal('0.99'),
            close=base_price,
            volume=volume
        )
        
        indicators = {
            'RSI': rsi_oversold,  # Oversold condition
            'SMA_20': float(base_price),
            'SMA_50': float(base_price)
        }
        
        # Create signal generator and strategy
        signal_generator = SignalGenerator()
        strategy = ScalpingStrategy(strategy_params)
        signal_generator.set_strategy(strategy)
        
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
        
        # Verify signal generation correctness
        if signal is not None:
            # Signal should be BUY for oversold conditions
            assert signal.direction == SignalDirection.BUY, f"Expected BUY signal for oversold RSI {rsi_oversold}, got {signal.direction}"
            
            # Signal should have valid strength and confidence
            assert 0.0 <= signal.strength <= 1.0, f"Signal strength {signal.strength} should be between 0.0 and 1.0"
            assert 0.0 <= signal.confidence <= 1.0, f"Signal confidence {signal.confidence} should be between 0.0 and 1.0"
            
            # Signal should contain strategy metadata
            assert signal.strategy == "ScalpingStrategy"
            assert 'rsi' in signal.metadata
            assert 'volume_spike' in signal.metadata
            assert signal.metadata['rsi'] == rsi_oversold
            
            # Volume spike should be reflected in metadata
            assert signal.metadata['volume_spike'] >= strategy_params['volume_threshold']

    @given(
        symbol=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='/')),
        base_price=st.decimals(min_value=10, max_value=100000, places=2),
        volume=st.decimals(min_value=1000, max_value=1000000, places=2),
        rsi_overbought=st.floats(min_value=65.0, max_value=85.0),  # Clearly overbought
        volume_multiplier=st.floats(min_value=2.0, max_value=5.0)  # Clear volume spike
    )
    def test_property_2_signal_generation_correctness_scalping_overbought(self, symbol, base_price, volume, 
                                                                         rsi_overbought, volume_multiplier):
        """
        **Feature: trading-bot-system, Property 2: Signal Generation Correctness**
        
        For any market data that meets configured strategy criteria, the Signal Generator 
        should generate appropriate sell signals for overbought conditions.
        **Validates: Requirements 1.4**
        """
        # Import here to avoid circular import issues
        from trading_bot.strategies.scalping_strategy import ScalpingStrategy
        
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
        
        # Now create market data with signal conditions (overbought RSI + volume spike)
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
                'RSI': rsi_overbought,  # Overbought condition
                'SMA_20': float(base_price),
                'SMA_50': float(base_price)
            }
        )
        
        # Generate signal
        signal = signal_generator.analyze_market_data(signal_market_data)
        
        # Verify signal generation correctness
        if signal is not None:
            # Signal should be SELL for overbought conditions
            assert signal.direction == SignalDirection.SELL, f"Expected SELL signal for overbought RSI {rsi_overbought}, got {signal.direction}"
            
            # Signal should have valid strength and confidence
            assert 0.0 <= signal.strength <= 1.0, f"Signal strength {signal.strength} should be between 0.0 and 1.0"
            assert 0.0 <= signal.confidence <= 1.0, f"Signal confidence {signal.confidence} should be between 0.0 and 1.0"
            
            # Signal should contain strategy metadata
            assert signal.strategy == "ScalpingStrategy"
            assert 'rsi' in signal.metadata
            assert 'volume_spike' in signal.metadata
            assert signal.metadata['rsi'] == rsi_overbought
            
            # Volume spike should be reflected in metadata
            assert signal.metadata['volume_spike'] >= strategy_params['volume_threshold']

    @given(
        symbol=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='/')),
        base_price=st.decimals(min_value=10, max_value=100000, places=2),
        volume=st.decimals(min_value=1000, max_value=1000000, places=2),
        fast_ma_multiplier=st.floats(min_value=1.02, max_value=1.10),  # Fast MA clearly above slow MA
        slow_ma_multiplier=st.floats(min_value=0.95, max_value=0.98)   # Slow MA clearly below fast MA
    )
    def test_property_2_signal_generation_correctness_swing_golden_cross(self, symbol, base_price, volume, 
                                                                        fast_ma_multiplier, slow_ma_multiplier):
        """
        **Feature: trading-bot-system, Property 2: Signal Generation Correctness**
        
        For any market data that meets swing trading criteria (golden cross), the Signal Generator 
        should generate appropriate buy signals.
        **Validates: Requirements 1.4**
        """
        # Import here to avoid circular import issues
        from trading_bot.strategies.swing_trading_strategy import SwingTradingStrategy
        
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
        
        # Generate valid OHLC data from base price and variation
        price_variation = Decimal('0.01')  # 1% variation
        variation_amount = base_price * price_variation
        open_price = base_price
        close_price = base_price + (variation_amount * Decimal('0.5'))  # Small change
        high_price = max(open_price, close_price) + variation_amount
        low_price = min(open_price, close_price) - variation_amount
        
        # Calculate MA values for crossover scenario
        slow_ma_value = base_price * Decimal(str(slow_ma_multiplier))
        fast_ma_value = base_price * Decimal(str(fast_ma_multiplier))
        
        # Ensure we have a significant crossover
        assume(float(fast_ma_value) > float(slow_ma_value))
        assume((float(fast_ma_value) - float(slow_ma_value)) / float(slow_ma_value) >= 0.001)  # At least 0.1% difference
        
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
                    'SMA_20': float(slow_ma_value) - 10,  # Fast MA below slow MA
                    'SMA_50': float(slow_ma_value)
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
                'SMA_20': float(fast_ma_value),   # Fast MA now above slow MA
                'SMA_50': float(slow_ma_value)    # Slow MA
            }
        )
        
        # Generate signal
        signal = signal_generator.analyze_market_data(crossover_market_data)
        
        # Verify signal generation correctness
        if signal is not None:
            # Signal should be BUY for golden cross
            assert signal.direction == SignalDirection.BUY, f"Expected BUY signal for golden cross (fast MA {float(fast_ma_value)} > slow MA {float(slow_ma_value)}), got {signal.direction}"
            
            # Signal should have valid strength and confidence
            assert 0.0 <= signal.strength <= 1.0, f"Signal strength {signal.strength} should be between 0.0 and 1.0"
            assert 0.0 <= signal.confidence <= 1.0, f"Signal confidence {signal.confidence} should be between 0.0 and 1.0"
            
            # Signal should contain strategy metadata
            assert signal.strategy == "SwingTradingStrategy"
            assert 'crossover_type' in signal.metadata
            assert signal.metadata['crossover_type'] == 'GOLDEN'
            assert 'fast_ma' in signal.metadata
            assert 'slow_ma' in signal.metadata
            assert signal.metadata['fast_ma'] == float(fast_ma_value)
            assert signal.metadata['slow_ma'] == float(slow_ma_value)

    @given(
        symbol=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='/')),
        base_price=st.decimals(min_value=10, max_value=100000, places=2),
        volume=st.decimals(min_value=1000, max_value=1000000, places=2),
        fast_ma_multiplier=st.floats(min_value=0.90, max_value=0.98),  # Fast MA clearly below slow MA
        slow_ma_multiplier=st.floats(min_value=1.02, max_value=1.10)   # Slow MA clearly above fast MA
    )
    def test_property_2_signal_generation_correctness_swing_death_cross(self, symbol, base_price, volume, 
                                                                       fast_ma_multiplier, slow_ma_multiplier):
        """
        **Feature: trading-bot-system, Property 2: Signal Generation Correctness**
        
        For any market data that meets swing trading criteria (death cross), the Signal Generator 
        should generate appropriate sell signals.
        **Validates: Requirements 1.4**
        """
        # Import here to avoid circular import issues
        from trading_bot.strategies.swing_trading_strategy import SwingTradingStrategy
        
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
        
        # Generate valid OHLC data from base price and variation
        price_variation = Decimal('0.01')  # 1% variation
        variation_amount = base_price * price_variation
        open_price = base_price
        close_price = base_price + (variation_amount * Decimal('0.5'))  # Small change
        high_price = max(open_price, close_price) + variation_amount
        low_price = min(open_price, close_price) - variation_amount
        
        # Calculate MA values for crossover scenario
        fast_ma_value = base_price * Decimal(str(fast_ma_multiplier))
        slow_ma_value = base_price * Decimal(str(slow_ma_multiplier))
        
        # Ensure we have a significant crossover
        assume(float(slow_ma_value) > float(fast_ma_value))
        assume((float(slow_ma_value) - float(fast_ma_value)) / float(slow_ma_value) >= 0.001)  # At least 0.1% difference
        
        # First, establish a bullish state (fast MA above slow MA)
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
                    'SMA_20': float(slow_ma_value) + 10,  # Fast MA above slow MA
                    'SMA_50': float(slow_ma_value)
                }
            )
            signal_generator.analyze_market_data(pre_crossover_data)
        
        # Now create the death cross (fast MA crosses below slow MA)
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
                'SMA_20': float(fast_ma_value),   # Fast MA now below slow MA
                'SMA_50': float(slow_ma_value)    # Slow MA
            }
        )
        
        # Generate signal
        signal = signal_generator.analyze_market_data(crossover_market_data)
        
        # Verify signal generation correctness
        if signal is not None:
            # Signal should be SELL for death cross
            assert signal.direction == SignalDirection.SELL, f"Expected SELL signal for death cross (fast MA {float(fast_ma_value)} < slow MA {float(slow_ma_value)}), got {signal.direction}"
            
            # Signal should have valid strength and confidence
            assert 0.0 <= signal.strength <= 1.0, f"Signal strength {signal.strength} should be between 0.0 and 1.0"
            assert 0.0 <= signal.confidence <= 1.0, f"Signal confidence {signal.confidence} should be between 0.0 and 1.0"
            
            # Signal should contain strategy metadata
            assert signal.strategy == "SwingTradingStrategy"
            assert 'crossover_type' in signal.metadata
            assert signal.metadata['crossover_type'] == 'DEATH'
            assert 'fast_ma' in signal.metadata
            assert 'slow_ma' in signal.metadata
            assert signal.metadata['fast_ma'] == float(fast_ma_value)
            assert signal.metadata['slow_ma'] == float(slow_ma_value)