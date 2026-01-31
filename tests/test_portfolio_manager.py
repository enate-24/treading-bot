"""Tests for Portfolio Manager implementation."""

import pytest
from decimal import Decimal
from datetime import datetime
from hypothesis import given, strategies as st
from trading_bot.portfolio_manager import PortfolioManager
from trading_bot.models import (
    TradingSignal, ExecutedTrade, Position, PortfolioMetrics,
    SignalDirection, OrderSide
)


class TestPortfolioManager:
    """Test cases for Portfolio Manager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.initial_capital = Decimal('10000')
        self.portfolio_manager = PortfolioManager(
            initial_capital=self.initial_capital,
            max_risk_per_trade=0.02
        )

    def test_initialization(self):
        """Test Portfolio Manager initialization."""
        assert self.portfolio_manager.get_available_capital() == self.initial_capital
        assert len(self.portfolio_manager.get_current_positions()) == 0
        
        metrics = self.portfolio_manager.get_portfolio_metrics()
        assert metrics.total_value == self.initial_capital
        assert metrics.available_capital == self.initial_capital
        assert metrics.unrealized_pnl == Decimal('0')
        assert metrics.realized_pnl == Decimal('0')
        assert metrics.positions_count == 0

    def test_calculate_position_size_basic(self):
        """Test basic position size calculation."""
        signal = TradingSignal(
            symbol="BTCUSD",
            direction=SignalDirection.BUY,
            strength=0.8,
            confidence=0.9,
            timestamp=datetime.now(),
            strategy="scalping",
            metadata={}
        )
        
        position_size = self.portfolio_manager.calculate_position_size(signal)
        
        # Should be positive and within reasonable bounds
        assert position_size > 0
        assert position_size <= self.initial_capital * Decimal('0.02')  # Max risk limit

    def test_calculate_position_size_with_signal_adjustment(self):
        """Test position size calculation with different signal strengths."""
        # Strong signal
        strong_signal = TradingSignal(
            symbol="BTCUSD",
            direction=SignalDirection.BUY,
            strength=1.0,
            confidence=1.0,
            timestamp=datetime.now(),
            strategy="scalping",
            metadata={}
        )
        
        # Weak signal
        weak_signal = TradingSignal(
            symbol="BTCUSD",
            direction=SignalDirection.BUY,
            strength=0.2,
            confidence=0.3,
            timestamp=datetime.now(),
            strategy="scalping",
            metadata={}
        )
        
        strong_size = self.portfolio_manager.calculate_position_size(strong_signal)
        weak_size = self.portfolio_manager.calculate_position_size(weak_signal)
        
        # Strong signal should result in larger position size
        assert strong_size > weak_size

    def test_update_position_new_long_position(self):
        """Test creating new long position."""
        trade = ExecutedTrade(
            trade_id="trade_1",
            symbol="BTCUSD",
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            fee=Decimal('5'),
            timestamp=datetime.now(),
            order_id="order_1"
        )
        
        initial_capital = self.portfolio_manager.get_available_capital()
        self.portfolio_manager.update_position(trade)
        
        positions = self.portfolio_manager.get_current_positions()
        assert len(positions) == 1
        
        position = positions[0]
        assert position.symbol == "BTCUSD"
        assert position.quantity == Decimal('0.1')
        assert position.entry_price == Decimal('50000')
        
        # Available capital should decrease
        expected_capital = initial_capital - (trade.quantity * trade.price + trade.fee)
        assert self.portfolio_manager.get_available_capital() == expected_capital

    def test_update_position_new_short_position(self):
        """Test creating new short position."""
        trade = ExecutedTrade(
            trade_id="trade_1",
            symbol="ETHUSD",
            side=OrderSide.SELL,
            quantity=Decimal('1.0'),
            price=Decimal('3000'),
            fee=Decimal('3'),
            timestamp=datetime.now(),
            order_id="order_1"
        )
        
        initial_capital = self.portfolio_manager.get_available_capital()
        self.portfolio_manager.update_position(trade)
        
        positions = self.portfolio_manager.get_current_positions()
        assert len(positions) == 1
        
        position = positions[0]
        assert position.symbol == "ETHUSD"
        assert position.quantity == Decimal('-1.0')  # Negative for short
        assert position.entry_price == Decimal('3000')
        
        # Available capital should increase for short sale (minus fees)
        expected_capital = initial_capital + (trade.quantity * trade.price - trade.fee)
        assert self.portfolio_manager.get_available_capital() == expected_capital

    def test_update_position_add_to_existing(self):
        """Test adding to existing position."""
        # First trade
        trade1 = ExecutedTrade(
            trade_id="trade_1",
            symbol="BTCUSD",
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            fee=Decimal('5'),
            timestamp=datetime.now(),
            order_id="order_1"
        )
        
        # Second trade - add to position
        trade2 = ExecutedTrade(
            trade_id="trade_2",
            symbol="BTCUSD",
            side=OrderSide.BUY,
            quantity=Decimal('0.05'),
            price=Decimal('52000'),
            fee=Decimal('2.6'),
            timestamp=datetime.now(),
            order_id="order_2"
        )
        
        self.portfolio_manager.update_position(trade1)
        self.portfolio_manager.update_position(trade2)
        
        positions = self.portfolio_manager.get_current_positions()
        assert len(positions) == 1
        
        position = positions[0]
        assert position.quantity == Decimal('0.15')  # Combined quantity
        
        # Check average entry price calculation
        expected_avg_price = (Decimal('0.1') * Decimal('50000') + Decimal('0.05') * Decimal('52000')) / Decimal('0.15')
        assert position.entry_price == expected_avg_price

    def test_update_position_close_position(self):
        """Test closing a position."""
        # Open position
        open_trade = ExecutedTrade(
            trade_id="trade_1",
            symbol="BTCUSD",
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            fee=Decimal('5'),
            timestamp=datetime.now(),
            order_id="order_1"
        )
        
        # Close position
        close_trade = ExecutedTrade(
            trade_id="trade_2",
            symbol="BTCUSD",
            side=OrderSide.SELL,
            quantity=Decimal('0.1'),
            price=Decimal('55000'),
            fee=Decimal('5.5'),
            timestamp=datetime.now(),
            order_id="order_2"
        )
        
        self.portfolio_manager.update_position(open_trade)
        assert len(self.portfolio_manager.get_current_positions()) == 1
        
        self.portfolio_manager.update_position(close_trade)
        assert len(self.portfolio_manager.get_current_positions()) == 0
        
        # Check realized PnL
        metrics = self.portfolio_manager.get_portfolio_metrics()
        expected_pnl = (Decimal('55000') - Decimal('50000')) * Decimal('0.1') - Decimal('5.5')
        assert metrics.realized_pnl == expected_pnl

    def test_update_position_prices(self):
        """Test updating position prices for unrealized PnL."""
        # Create position
        trade = ExecutedTrade(
            trade_id="trade_1",
            symbol="BTCUSD",
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            fee=Decimal('5'),
            timestamp=datetime.now(),
            order_id="order_1"
        )
        
        self.portfolio_manager.update_position(trade)
        
        # Update price
        new_price = Decimal('55000')
        self.portfolio_manager.update_position_prices("BTCUSD", new_price)
        
        position = self.portfolio_manager.get_current_positions()[0]
        assert position.current_price == new_price
        
        expected_unrealized_pnl = (new_price - Decimal('50000')) * Decimal('0.1')
        assert position.unrealized_pnl == expected_unrealized_pnl

    def test_get_position_correlation(self):
        """Test position correlation calculation."""
        # Create two long positions
        trade1 = ExecutedTrade(
            trade_id="trade_1",
            symbol="BTCUSD",
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            fee=Decimal('5'),
            timestamp=datetime.now(),
            order_id="order_1"
        )
        
        trade2 = ExecutedTrade(
            trade_id="trade_2",
            symbol="ETHUSD",
            side=OrderSide.BUY,
            quantity=Decimal('1.0'),
            price=Decimal('3000'),
            fee=Decimal('3'),
            timestamp=datetime.now(),
            order_id="order_2"
        )
        
        self.portfolio_manager.update_position(trade1)
        self.portfolio_manager.update_position(trade2)
        
        correlation = self.portfolio_manager.get_position_correlation(["BTCUSD", "ETHUSD"])
        
        # Same direction positions should have positive correlation
        assert correlation["BTCUSD"]["ETHUSD"] == 0.5
        assert correlation["ETHUSD"]["BTCUSD"] == 0.5
        
        # Self-correlation should be 1.0
        assert correlation["BTCUSD"]["BTCUSD"] == 1.0
        assert correlation["ETHUSD"]["ETHUSD"] == 1.0

    def test_get_total_exposure(self):
        """Test total portfolio exposure calculation."""
        # Create positions
        trade1 = ExecutedTrade(
            trade_id="trade_1",
            symbol="BTCUSD",
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            fee=Decimal('5'),
            timestamp=datetime.now(),
            order_id="order_1"
        )
        
        trade2 = ExecutedTrade(
            trade_id="trade_2",
            symbol="ETHUSD",
            side=OrderSide.SELL,
            quantity=Decimal('1.0'),
            price=Decimal('3000'),
            fee=Decimal('3'),
            timestamp=datetime.now(),
            order_id="order_2"
        )
        
        self.portfolio_manager.update_position(trade1)
        self.portfolio_manager.update_position(trade2)
        
        # Update current prices
        self.portfolio_manager.update_position_prices("BTCUSD", Decimal('52000'))
        self.portfolio_manager.update_position_prices("ETHUSD", Decimal('2900'))
        
        total_exposure = self.portfolio_manager.get_total_exposure()
        expected_exposure = Decimal('0.1') * Decimal('52000') + Decimal('1.0') * Decimal('2900')
        assert total_exposure == expected_exposure

    def test_get_position_by_symbol(self):
        """Test getting position by symbol."""
        trade = ExecutedTrade(
            trade_id="trade_1",
            symbol="BTCUSD",
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            fee=Decimal('5'),
            timestamp=datetime.now(),
            order_id="order_1"
        )
        
        self.portfolio_manager.update_position(trade)
        
        position = self.portfolio_manager.get_position_by_symbol("BTCUSD")
        assert position is not None
        assert position.symbol == "BTCUSD"
        
        # Non-existent position should return None
        non_existent = self.portfolio_manager.get_position_by_symbol("NONEXISTENT")
        assert non_existent is None

    def test_kelly_criterion_edge_cases(self):
        """Test Kelly Criterion calculation edge cases."""
        # Test with zero win/loss ratio
        kelly_fraction = self.portfolio_manager._calculate_kelly_fraction(0.6, 0.0)
        assert kelly_fraction == 0.0
        
        # Test with negative win/loss ratio
        kelly_fraction = self.portfolio_manager._calculate_kelly_fraction(0.6, -1.0)
        assert kelly_fraction == 0.0
        
        # Test with very high Kelly fraction (should be capped)
        kelly_fraction = self.portfolio_manager._calculate_kelly_fraction(0.9, 10.0)
        assert kelly_fraction == 0.25  # Should be capped at 25%

    def test_portfolio_metrics_with_positions(self):
        """Test portfolio metrics calculation with active positions."""
        # Create position
        trade = ExecutedTrade(
            trade_id="trade_1",
            symbol="BTCUSD",
            side=OrderSide.BUY,
            quantity=Decimal('0.1'),
            price=Decimal('50000'),
            fee=Decimal('5'),
            timestamp=datetime.now(),
            order_id="order_1"
        )
        
        self.portfolio_manager.update_position(trade)
        
        # Update price for unrealized PnL
        self.portfolio_manager.update_position_prices("BTCUSD", Decimal('55000'))
        
        metrics = self.portfolio_manager.get_portfolio_metrics()
        
        expected_unrealized_pnl = (Decimal('55000') - Decimal('50000')) * Decimal('0.1')
        expected_available_capital = self.initial_capital - (trade.quantity * trade.price + trade.fee)
        expected_total_value = expected_available_capital + expected_unrealized_pnl
        
        assert metrics.unrealized_pnl == expected_unrealized_pnl
        assert metrics.available_capital == expected_available_capital
        assert metrics.total_value == expected_total_value
        assert metrics.positions_count == 1


class TestPortfolioManagerProperties:
    """Property-based tests for Portfolio Manager."""

    @given(
        initial_capital=st.decimals(min_value=1000, max_value=1000000, places=2),
        max_risk_per_trade=st.floats(min_value=0.001, max_value=0.1),  # 0.1% to 10%
        signal_strength=st.floats(min_value=0.0, max_value=1.0),
        signal_confidence=st.floats(min_value=0.0, max_value=1.0),
        symbol=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='/')),
        strategy=st.sampled_from(['scalping', 'swing_trading', 'momentum'])
    )
    def test_position_sizing_accuracy_property(
        self, 
        initial_capital: Decimal, 
        max_risk_per_trade: float,
        signal_strength: float,
        signal_confidence: float,
        symbol: str,
        strategy: str
    ):
        """
        **Feature: trading-bot-system, Property 3: Position Sizing Accuracy**
        
        *For any* portfolio state and risk parameters, the Portfolio Manager should 
        calculate position sizes that never exceed the configured maximum risk per trade percentage.
        
        **Validates: Requirements 1.5, 3.4**
        """
        # Create portfolio manager with given parameters
        portfolio_manager = PortfolioManager(
            initial_capital=initial_capital,
            max_risk_per_trade=max_risk_per_trade
        )
        
        # Create trading signal with given parameters
        signal = TradingSignal(
            symbol=symbol,
            direction=SignalDirection.BUY,
            strength=signal_strength,
            confidence=signal_confidence,
            timestamp=datetime.now(),
            strategy=strategy,
            metadata={}
        )
        
        # Calculate position size
        position_size = portfolio_manager.calculate_position_size(signal)
        
        # Property: Position size should never exceed maximum risk per trade
        max_allowed_position = initial_capital * Decimal(str(max_risk_per_trade))
        
        # Core property assertion
        assert position_size <= max_allowed_position, (
            f"Position size {position_size} exceeds maximum allowed {max_allowed_position} "
            f"(risk: {max_risk_per_trade}, capital: {initial_capital})"
        )
        
        # Additional invariants
        assert position_size > 0, "Position size must be positive"
        
        # Position size should be reasonable (at least minimum position)
        min_position = initial_capital * Decimal('0.001')  # 0.1% minimum
        assert position_size >= min_position, (
            f"Position size {position_size} is below minimum {min_position}"
        )
        
        # Position size should scale with signal strength and confidence
        # Test with zero signal strength/confidence
        zero_signal = TradingSignal(
            symbol=symbol,
            direction=SignalDirection.BUY,
            strength=0.0,
            confidence=0.0,
            timestamp=datetime.now(),
            strategy=strategy,
            metadata={}
        )
        
        zero_position_size = portfolio_manager.calculate_position_size(zero_signal)
        
        # Zero signal should result in minimum position size
        assert zero_position_size == min_position, (
            f"Zero signal should result in minimum position size {min_position}, got {zero_position_size}"
        )

    @given(
        initial_capital=st.decimals(min_value=1000, max_value=100000, places=2),
        max_risk_per_trade=st.floats(min_value=0.01, max_value=0.05),  # 1% to 5%
        num_positions=st.integers(min_value=1, max_value=10),
        trade_prices=st.lists(
            st.decimals(min_value=10, max_value=10000, places=2),
            min_size=1,
            max_size=10
        ),
        trade_quantities=st.lists(
            st.decimals(min_value=0.001, max_value=10, places=6),
            min_size=1,
            max_size=10
        )
    )
    def test_position_sizing_with_existing_positions_property(
        self,
        initial_capital: Decimal,
        max_risk_per_trade: float,
        num_positions: int,
        trade_prices: list,
        trade_quantities: list
    ):
        """
        **Feature: trading-bot-system, Property 3: Position Sizing Accuracy**
        
        Test that position sizing respects risk limits even with existing positions.
        
        **Validates: Requirements 1.5, 3.4**
        """
        # Ensure we have enough data
        if len(trade_prices) < num_positions or len(trade_quantities) < num_positions:
            return
        
        portfolio_manager = PortfolioManager(
            initial_capital=initial_capital,
            max_risk_per_trade=max_risk_per_trade
        )
        
        # Create some existing positions
        for i in range(min(num_positions, len(trade_prices), len(trade_quantities))):
            trade = ExecutedTrade(
                trade_id=f"trade_{i}",
                symbol=f"SYMBOL{i}",
                side=OrderSide.BUY,
                quantity=trade_quantities[i],
                price=trade_prices[i],
                fee=trade_prices[i] * trade_quantities[i] * Decimal('0.001'),  # 0.1% fee
                timestamp=datetime.now(),
                order_id=f"order_{i}"
            )
            portfolio_manager.update_position(trade)
        
        # Create new signal for position sizing
        signal = TradingSignal(
            symbol="NEWSYMBOL",
            direction=SignalDirection.BUY,
            strength=0.8,
            confidence=0.9,
            timestamp=datetime.now(),
            strategy="scalping",
            metadata={}
        )
        
        # Calculate position size
        position_size = portfolio_manager.calculate_position_size(signal)
        
        # Property: Position size should still respect maximum risk per trade
        # based on original capital, not remaining capital
        max_allowed_position = initial_capital * Decimal(str(max_risk_per_trade))
        
        assert position_size <= max_allowed_position, (
            f"Position size {position_size} exceeds maximum allowed {max_allowed_position} "
            f"even with existing positions"
        )
        
        # Position size should be positive
        assert position_size > 0, "Position size must be positive"