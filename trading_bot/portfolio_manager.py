"""Portfolio Manager implementation for position and risk management."""

import math
from typing import List, Dict
from decimal import Decimal
from datetime import datetime
from .interfaces.portfolio_manager import IPortfolioManager
from .models import TradingSignal, Position, ExecutedTrade, PortfolioMetrics, OrderSide


class PortfolioManager(IPortfolioManager):
    """Portfolio Manager implementation with Kelly Criterion position sizing."""

    def __init__(self, initial_capital: Decimal, max_risk_per_trade: float = 0.02):
        """Initialize Portfolio Manager.
        
        Args:
            initial_capital: Starting capital amount
            max_risk_per_trade: Maximum risk per trade as percentage (default 2%)
        """
        self._initial_capital = initial_capital
        self._available_capital = initial_capital
        self._max_risk_per_trade = max_risk_per_trade
        self._positions: Dict[str, Position] = {}
        self._trade_history: List[ExecutedTrade] = []
        self._realized_pnl = Decimal('0')
        
        # Kelly Criterion parameters
        self._win_rate_history: Dict[str, List[bool]] = {}
        self._avg_win_loss_ratio: Dict[str, float] = {}

    def calculate_position_size(self, signal: TradingSignal) -> Decimal:
        """Calculate optimal position size using Kelly Criterion.
        
        The Kelly Criterion formula: f = (bp - q) / b
        Where:
        - f = fraction of capital to wager
        - b = odds received on the wager (avg_win / avg_loss)
        - p = probability of winning (win_rate)
        - q = probability of losing (1 - p)
        
        Args:
            signal: Trading signal with strength and confidence
            
        Returns:
            Position size in base currency
        """
        # Get historical performance for this symbol/strategy
        strategy_key = f"{signal.symbol}_{signal.strategy}"
        
        # Use default values if no history
        win_rate = self._get_win_rate(strategy_key)
        win_loss_ratio = self._get_win_loss_ratio(strategy_key)
        
        # Calculate Kelly fraction
        kelly_fraction = self._calculate_kelly_fraction(win_rate, win_loss_ratio)
        
        # Adjust by signal strength and confidence
        signal_adjustment = signal.strength * signal.confidence
        adjusted_kelly = kelly_fraction * signal_adjustment
        
        # Apply maximum risk limit
        risk_fraction = min(adjusted_kelly, self._max_risk_per_trade)
        
        # Ensure positive position size
        risk_fraction = max(risk_fraction, 0.001)  # Minimum 0.1% position
        
        # Calculate position size based on available capital
        # Ensure we don't calculate negative position sizes
        if self._available_capital <= 0:
            # If no available capital, return minimum position size based on initial capital
            position_size = self._initial_capital * Decimal('0.001')  # 0.1% minimum
        else:
            position_size = self._available_capital * Decimal(str(risk_fraction))
        
        # Ensure position size is always positive and reasonable
        min_position = self._initial_capital * Decimal('0.001')  # 0.1% of initial capital
        position_size = max(position_size, min_position)
        
        return position_size

    def get_current_positions(self) -> List[Position]:
        """Get all current open positions.
        
        Returns:
            List of current positions
        """
        return list(self._positions.values())

    def get_available_capital(self) -> Decimal:
        """Get available capital for new positions.
        
        Returns:
            Available capital amount
        """
        return self._available_capital

    def update_position(self, trade: ExecutedTrade) -> None:
        """Update position based on executed trade.
        
        Args:
            trade: Executed trade information
        """
        symbol = trade.symbol
        
        if symbol in self._positions:
            position = self._positions[symbol]
            
            if trade.side == OrderSide.BUY:
                # Adding to position or opening new long
                total_quantity = position.quantity + trade.quantity
                if total_quantity > 0:
                    # Calculate new average entry price
                    total_cost = (position.quantity * position.entry_price + 
                                trade.quantity * trade.price)
                    position.entry_price = total_cost / total_quantity
                    position.quantity = total_quantity
                else:
                    # Position closed or reversed
                    self._close_position(symbol, trade)
            else:  # SELL
                if position.quantity >= trade.quantity:
                    # Reducing or closing position
                    if position.quantity == trade.quantity:
                        # Closing position completely
                        self._close_position(symbol, trade)
                    else:
                        # Partially reducing position
                        position.quantity -= trade.quantity
                else:
                    # Position reversed
                    remaining_quantity = trade.quantity - position.quantity
                    self._close_position(symbol, trade)
                    # Create new short position
                    self._positions[symbol] = Position(
                        symbol=symbol,
                        quantity=-remaining_quantity,
                        entry_price=trade.price,
                        current_price=trade.price,
                        unrealized_pnl=Decimal('0'),
                        stop_loss=None,
                        take_profit=None,
                        timestamp=trade.timestamp
                    )
        else:
            # New position
            quantity = trade.quantity if trade.side == OrderSide.BUY else -trade.quantity
            self._positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                entry_price=trade.price,
                current_price=trade.price,
                unrealized_pnl=Decimal('0'),
                stop_loss=None,
                take_profit=None,
                timestamp=trade.timestamp
            )
        
        # Update available capital
        if trade.side == OrderSide.BUY:
            # Buying reduces available capital
            trade_value = trade.quantity * trade.price + trade.fee
            self._available_capital -= trade_value
        else:
            # Selling increases available capital (minus fees)
            trade_value = trade.quantity * trade.price - trade.fee
            self._available_capital += trade_value
        
        # Record trade for performance tracking
        self._trade_history.append(trade)

    def get_portfolio_metrics(self) -> PortfolioMetrics:
        """Get current portfolio performance metrics.
        
        Returns:
            Portfolio metrics including PnL and positions
        """
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self._positions.values())
        total_value = self._available_capital + unrealized_pnl
        
        return PortfolioMetrics(
            total_value=total_value,
            available_capital=self._available_capital,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=self._realized_pnl,
            positions_count=len(self._positions),
            timestamp=datetime.now()
        )

    def update_position_prices(self, symbol: str, current_price: Decimal) -> None:
        """Update current price for a position to calculate unrealized PnL.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
        """
        if symbol in self._positions:
            position = self._positions[symbol]
            position.current_price = current_price
            
            # Calculate unrealized PnL
            if position.quantity > 0:  # Long position
                position.unrealized_pnl = (current_price - position.entry_price) * position.quantity
            else:  # Short position
                position.unrealized_pnl = (position.entry_price - current_price) * abs(position.quantity)

    def get_position_correlation(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """Calculate position correlation matrix.
        
        Args:
            symbols: List of symbols to analyze
            
        Returns:
            Correlation matrix as nested dictionary
        """
        # Simplified correlation analysis based on position sizes
        correlation_matrix = {}
        
        for symbol1 in symbols:
            correlation_matrix[symbol1] = {}
            for symbol2 in symbols:
                if symbol1 == symbol2:
                    correlation_matrix[symbol1][symbol2] = 1.0
                else:
                    # Simplified correlation based on position exposure
                    pos1 = self._positions.get(symbol1)
                    pos2 = self._positions.get(symbol2)
                    
                    if pos1 and pos2:
                        # Same direction positions have positive correlation
                        if (pos1.quantity > 0) == (pos2.quantity > 0):
                            correlation_matrix[symbol1][symbol2] = 0.5
                        else:
                            correlation_matrix[symbol1][symbol2] = -0.5
                    else:
                        correlation_matrix[symbol1][symbol2] = 0.0
        
        return correlation_matrix

    def _calculate_kelly_fraction(self, win_rate: float, win_loss_ratio: float) -> float:
        """Calculate Kelly Criterion fraction.
        
        Args:
            win_rate: Historical win rate (0.0 to 1.0)
            win_loss_ratio: Average win to average loss ratio
            
        Returns:
            Kelly fraction (can be negative)
        """
        if win_loss_ratio <= 0:
            return 0.0
        
        # Kelly formula: f = (bp - q) / b
        # where b = win_loss_ratio, p = win_rate, q = 1 - win_rate
        kelly_fraction = (win_loss_ratio * win_rate - (1 - win_rate)) / win_loss_ratio
        
        # Cap Kelly fraction to prevent over-leveraging
        return max(min(kelly_fraction, 0.25), 0.0)  # Max 25% of capital

    def _get_win_rate(self, strategy_key: str) -> float:
        """Get historical win rate for strategy.
        
        Args:
            strategy_key: Strategy identifier
            
        Returns:
            Win rate (default 0.5 if no history)
        """
        if strategy_key not in self._win_rate_history or not self._win_rate_history[strategy_key]:
            return 0.5  # Default 50% win rate
        
        wins = sum(self._win_rate_history[strategy_key])
        total = len(self._win_rate_history[strategy_key])
        return wins / total if total > 0 else 0.5

    def _get_win_loss_ratio(self, strategy_key: str) -> float:
        """Get historical win/loss ratio for strategy.
        
        Args:
            strategy_key: Strategy identifier
            
        Returns:
            Win/loss ratio (default 1.5 if no history)
        """
        return self._avg_win_loss_ratio.get(strategy_key, 1.5)  # Default 1.5:1 ratio

    def _close_position(self, symbol: str, trade: ExecutedTrade) -> None:
        """Close a position and calculate realized PnL.
        
        Args:
            symbol: Trading symbol
            trade: Trade that closes the position
        """
        if symbol in self._positions:
            position = self._positions[symbol]
            
            # Calculate realized PnL based on the trade quantity (not full position)
            trade_quantity = min(abs(position.quantity), trade.quantity)
            
            if position.quantity > 0:  # Closing long position with sell
                pnl = (trade.price - position.entry_price) * trade_quantity
            else:  # Closing short position with buy
                pnl = (position.entry_price - trade.price) * trade_quantity
            
            # Subtract fees from the closing trade only (opening trade fees already accounted for)
            pnl -= trade.fee
            
            self._realized_pnl += pnl
            
            # Update win/loss tracking
            strategy_key = f"{symbol}_{trade.order_id.split('_')[0] if '_' in trade.order_id else 'unknown'}"
            is_win = pnl > 0
            
            if strategy_key not in self._win_rate_history:
                self._win_rate_history[strategy_key] = []
            
            self._win_rate_history[strategy_key].append(is_win)
            
            # Keep only last 100 trades for each strategy
            if len(self._win_rate_history[strategy_key]) > 100:
                self._win_rate_history[strategy_key] = self._win_rate_history[strategy_key][-100:]
            
            # Remove position
            del self._positions[symbol]

    def get_total_exposure(self) -> Decimal:
        """Get total portfolio exposure across all positions.
        
        Returns:
            Total exposure amount
        """
        total_exposure = Decimal('0')
        for position in self._positions.values():
            exposure = abs(position.quantity * position.current_price)
            total_exposure += exposure
        return total_exposure

    def get_position_by_symbol(self, symbol: str) -> Position:
        """Get position for specific symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Position object or None if not found
        """
        return self._positions.get(symbol)