"""Risk Manager implementation for comprehensive risk control."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from threading import Lock

from .interfaces.risk_manager import IRiskManager, RiskValidationResult
from .interfaces.portfolio_manager import IPortfolioManager
from .models import OrderRequest, RiskMetrics, Position, OrderSide


class RiskManager(IRiskManager):
    """Risk Manager with comprehensive risk controls."""
    
    def __init__(self, portfolio_manager: IPortfolioManager, config: Dict[str, Any]):
        """Initialize Risk Manager.
        
        Args:
            portfolio_manager: Portfolio manager instance
            config: Risk management configuration
        """
        self.portfolio_manager = portfolio_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._lock = Lock()
        
        # Risk parameters from config
        self.max_risk_per_trade = config.get('max_risk_per_trade', 0.02)  # 2%
        self.max_portfolio_drawdown = config.get('max_portfolio_drawdown', 0.10)  # 10%
        self.daily_loss_limit = config.get('daily_loss_limit', 0.05)  # 5%
        self.max_position_correlation = config.get('max_position_correlation', 0.7)
        self.emergency_stop_drawdown = config.get('emergency_stop_drawdown', 0.15)  # 15%
        
        # Risk state tracking
        self.emergency_stop_active = False
        self.daily_start_capital = Decimal('0')
        self.daily_pnl = Decimal('0')
        self.max_drawdown_today = 0.0
        self.position_stops: Dict[str, Decimal] = {}
        
        # Initialize daily tracking
        self._initialize_daily_tracking()
    
    def _initialize_daily_tracking(self) -> None:
        """Initialize daily risk tracking."""
        try:
            portfolio_metrics = self.portfolio_manager.get_portfolio_metrics()
            self.daily_start_capital = portfolio_metrics.total_value
            self.daily_pnl = Decimal('0')
            self.max_drawdown_today = 0.0
            self.logger.info(f"Initialized daily tracking with capital: {self.daily_start_capital}")
        except Exception as e:
            self.logger.error(f"Failed to initialize daily tracking: {e}")
            self.daily_start_capital = Decimal('100000')  # Default fallback
    
    def validate_trade(self, trade_request: OrderRequest) -> RiskValidationResult:
        """Validate a trade request against risk parameters.
        
        Args:
            trade_request: Order request to validate
            
        Returns:
            Risk validation result with approval status
        """
        with self._lock:
            try:
                # Check if emergency stop is active
                if self.emergency_stop_active:
                    return RiskValidationResult(False, "Emergency stop is active")
                
                # Check daily loss limit
                if not self._check_daily_loss_limit():
                    return RiskValidationResult(False, "Daily loss limit exceeded")
                
                # Check portfolio drawdown
                if not self._check_portfolio_drawdown():
                    return RiskValidationResult(False, "Portfolio drawdown limit exceeded")
                
                # Check position size risk
                if not self._check_position_size_risk(trade_request):
                    return RiskValidationResult(False, "Position size exceeds risk per trade limit")
                
                # Check available capital
                if not self._check_available_capital(trade_request):
                    return RiskValidationResult(False, "Insufficient available capital")
                
                # Check position correlation (simplified check)
                if not self._check_position_correlation(trade_request):
                    return RiskValidationResult(False, "Position would exceed correlation limits")
                
                self.logger.info(f"Trade validated successfully: {trade_request.symbol} {trade_request.side}")
                return RiskValidationResult(True, "Trade approved")
                
            except Exception as e:
                self.logger.error(f"Error validating trade: {e}")
                return RiskValidationResult(False, f"Validation error: {str(e)}")
    
    def _check_daily_loss_limit(self) -> bool:
        """Check if daily loss limit is exceeded."""
        try:
            portfolio_metrics = self.portfolio_manager.get_portfolio_metrics()
            current_value = portfolio_metrics.total_value
            
            if self.daily_start_capital > 0:
                daily_return = (current_value - self.daily_start_capital) / self.daily_start_capital
                if daily_return < -self.daily_loss_limit:
                    self.logger.warning(f"Daily loss limit exceeded: {daily_return:.2%}")
                    return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error checking daily loss limit: {e}")
            return False
    
    def _check_portfolio_drawdown(self) -> bool:
        """Check if portfolio drawdown limit is exceeded."""
        try:
            risk_metrics = self.get_risk_metrics()
            if risk_metrics.current_drawdown > self.max_portfolio_drawdown:
                self.logger.warning(f"Portfolio drawdown limit exceeded: {risk_metrics.current_drawdown:.2%}")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Error checking portfolio drawdown: {e}")
            return False
    
    def _check_position_size_risk(self, trade_request: OrderRequest) -> bool:
        """Check if position size exceeds risk per trade limit."""
        try:
            portfolio_metrics = self.portfolio_manager.get_portfolio_metrics()
            total_value = portfolio_metrics.total_value
            
            # Calculate position value
            position_value = trade_request.quantity * (trade_request.price or Decimal('0'))
            
            # Calculate risk as percentage of portfolio
            if total_value > 0:
                position_risk = position_value / total_value
                if position_risk > Decimal(str(self.max_risk_per_trade)):
                    self.logger.warning(f"Position size risk too high: {position_risk:.2%}")
                    return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error checking position size risk: {e}")
            return False
    
    def _check_available_capital(self, trade_request: OrderRequest) -> bool:
        """Check if sufficient capital is available."""
        try:
            available_capital = self.portfolio_manager.get_available_capital()
            required_capital = trade_request.quantity * (trade_request.price or Decimal('0'))
            
            if required_capital > available_capital:
                self.logger.warning(f"Insufficient capital: required {required_capital}, available {available_capital}")
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error checking available capital: {e}")
            return False
    
    def _check_position_correlation(self, trade_request: OrderRequest) -> bool:
        """Check position correlation limits (simplified implementation)."""
        try:
            positions = self.portfolio_manager.get_current_positions()
            
            # Simple correlation check: limit number of positions in same direction
            same_direction_count = sum(1 for pos in positions 
                                    if (pos.quantity > 0 and trade_request.side == OrderSide.BUY) or
                                       (pos.quantity < 0 and trade_request.side == OrderSide.SELL))
            
            # Allow maximum 5 positions in same direction (simplified rule)
            if same_direction_count >= 5:
                self.logger.warning(f"Too many positions in same direction: {same_direction_count}")
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error checking position correlation: {e}")
            return True  # Allow trade if correlation check fails
    
    def monitor_positions(self) -> None:
        """Monitor all positions for risk limit violations."""
        with self._lock:
            try:
                positions = self.portfolio_manager.get_current_positions()
                
                for position in positions:
                    self._check_stop_loss(position)
                    self._check_take_profit(position)
                
                # Check for emergency conditions
                self._check_emergency_conditions()
                
            except Exception as e:
                self.logger.error(f"Error monitoring positions: {e}")
    
    def _check_stop_loss(self, position: Position) -> None:
        """Check and enforce stop loss for a position."""
        try:
            if position.stop_loss is None:
                return
            
            # Check if stop loss should be triggered
            should_trigger = False
            if position.quantity > 0:  # Long position
                should_trigger = position.current_price <= position.stop_loss
            else:  # Short position
                should_trigger = position.current_price >= position.stop_loss
            
            if should_trigger:
                self.logger.warning(f"Stop loss triggered for {position.symbol}: "
                                  f"current {position.current_price}, stop {position.stop_loss}")
                self._trigger_position_close(position, "Stop loss triggered")
                
        except Exception as e:
            self.logger.error(f"Error checking stop loss for {position.symbol}: {e}")
    
    def _check_take_profit(self, position: Position) -> None:
        """Check and enforce take profit for a position."""
        try:
            if position.take_profit is None:
                return
            
            # Check if take profit should be triggered
            should_trigger = False
            if position.quantity > 0:  # Long position
                should_trigger = position.current_price >= position.take_profit
            else:  # Short position
                should_trigger = position.current_price <= position.take_profit
            
            if should_trigger:
                self.logger.info(f"Take profit triggered for {position.symbol}: "
                               f"current {position.current_price}, target {position.take_profit}")
                self._trigger_position_close(position, "Take profit triggered")
                
        except Exception as e:
            self.logger.error(f"Error checking take profit for {position.symbol}: {e}")
    
    def _trigger_position_close(self, position: Position, reason: str) -> None:
        """Trigger position close (placeholder for execution engine integration)."""
        # This would integrate with execution engine to close position
        self.logger.info(f"Position close triggered: {position.symbol}, reason: {reason}")
        # TODO: Integrate with execution engine when implemented
    
    def _check_emergency_conditions(self) -> None:
        """Check for emergency conditions that require immediate action."""
        try:
            risk_metrics = self.get_risk_metrics()
            
            # Check if emergency drawdown threshold is exceeded
            if risk_metrics.current_drawdown > self.emergency_stop_drawdown:
                self.trigger_emergency_stop(f"Emergency drawdown exceeded: {risk_metrics.current_drawdown:.2%}")
            
        except Exception as e:
            self.logger.error(f"Error checking emergency conditions: {e}")
    
    def trigger_emergency_stop(self, reason: str) -> None:
        """Trigger emergency stop to halt all trading.
        
        Args:
            reason: Reason for emergency stop
        """
        with self._lock:
            if not self.emergency_stop_active:
                self.emergency_stop_active = True
                self.logger.critical(f"EMERGENCY STOP ACTIVATED: {reason}")
                
                # Close all positions (placeholder)
                try:
                    positions = self.portfolio_manager.get_current_positions()
                    for position in positions:
                        self._trigger_position_close(position, f"Emergency stop: {reason}")
                except Exception as e:
                    self.logger.error(f"Error closing positions during emergency stop: {e}")
    
    def update_stop_loss(self, position_id: str, new_stop: Decimal) -> None:
        """Update stop loss for a position.
        
        Args:
            position_id: Position identifier (using symbol as ID for now)
            new_stop: New stop loss price
        """
        with self._lock:
            try:
                self.position_stops[position_id] = new_stop
                self.logger.info(f"Updated stop loss for {position_id}: {new_stop}")
                
                # TODO: Update position in portfolio manager when method is available
                
            except Exception as e:
                self.logger.error(f"Error updating stop loss for {position_id}: {e}")
    
    def get_risk_metrics(self) -> RiskMetrics:
        """Get current risk metrics.
        
        Returns:
            Current risk metrics including drawdown and exposure
        """
        try:
            portfolio_metrics = self.portfolio_manager.get_portfolio_metrics()
            positions = self.portfolio_manager.get_current_positions()
            
            # Calculate current drawdown
            current_value = portfolio_metrics.total_value
            if self.daily_start_capital > 0:
                daily_return = (current_value - self.daily_start_capital) / self.daily_start_capital
                current_drawdown = max(0, -float(daily_return))
            else:
                current_drawdown = 0.0
            
            # Update max drawdown
            self.max_drawdown_today = max(self.max_drawdown_today, current_drawdown)
            
            # Calculate portfolio risk (simplified as total position value / total capital)
            total_position_value = sum(abs(pos.quantity * pos.current_price) for pos in positions)
            portfolio_risk = float(total_position_value / current_value) if current_value > 0 else 0.0
            
            # Calculate individual position risks
            position_risk = {}
            for pos in positions:
                position_value = abs(pos.quantity * pos.current_price)
                risk_pct = float(position_value / current_value) if current_value > 0 else 0.0
                position_risk[pos.symbol] = risk_pct
            
            # Calculate daily PnL
            daily_pnl = current_value - self.daily_start_capital
            
            return RiskMetrics(
                current_drawdown=current_drawdown,
                max_drawdown=self.max_drawdown_today,
                daily_pnl=daily_pnl,
                portfolio_risk=portfolio_risk,
                position_risk=position_risk,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {e}")
            return RiskMetrics(
                current_drawdown=0.0,
                max_drawdown=0.0,
                daily_pnl=Decimal('0'),
                portfolio_risk=0.0,
                position_risk={},
                timestamp=datetime.now()
            )
    
    def reset_emergency_stop(self) -> None:
        """Reset emergency stop (for administrative use)."""
        with self._lock:
            self.emergency_stop_active = False
            self.logger.info("Emergency stop reset")
    
    def reset_daily_tracking(self) -> None:
        """Reset daily tracking (typically called at start of new trading day)."""
        with self._lock:
            self._initialize_daily_tracking()
            self.logger.info("Daily risk tracking reset")