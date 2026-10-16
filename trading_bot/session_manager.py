"""Session Manager for session-based trading configuration."""

import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass


logger = logging.getLogger(__name__)


class TradingSession(Enum):
    """Trading session types."""
    ASIAN = "asian"
    LONDON = "london"
    NEW_YORK = "new_york"
    OVERLAP = "overlap"  # London/NY overlap
    QUIET = "quiet"
    CLOSED = "closed"


@dataclass
class SessionConfig:
    """Configuration for a trading session."""
    name: str
    start_time: time  # GMT
    end_time: time    # GMT
    liquidity: str    # "low", "medium", "high", "very_high"
    volatility: str   # "low", "medium", "high"
    best_pairs: List[str]
    max_positions: int
    risk_per_trade: float
    min_confidence: float
    enabled: bool = True
    
    # HFT-specific parameters
    tick_threshold: float = 0.00001
    volume_multiplier: float = 1.2
    spread_threshold: float = 0.00003
    profit_target: float = 0.0003
    stop_loss: float = 0.0002


class SessionManager:
    """Manages trading sessions and adjusts bot behavior accordingly."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize session manager.
        
        Args:
            config: Session configuration
        """
        self.config = config
        self.sessions = self._initialize_sessions()
        self.current_session: Optional[TradingSession] = None
        self.session_config: Optional[SessionConfig] = None
        
        logger.info("Session Manager initialized")
    
    def _initialize_sessions(self) -> Dict[TradingSession, SessionConfig]:
        """Initialize session configurations."""
        sessions = {}
        
        # Asian Session (00:00 - 08:00 GMT)
        sessions[TradingSession.ASIAN] = SessionConfig(
            name="Asian Session",
            start_time=time(0, 0),
            end_time=time(8, 0),
            liquidity="low",
            volatility="low",
            best_pairs=["USDJPYm", "AUDJPYm", "NZDJPYm", "AUDUSDm", "XAUUSDm"],
            max_positions=2,
            risk_per_trade=0.005,  # 0.5% (lower risk in quiet session)
            min_confidence=0.35,    # Higher confidence needed
            tick_threshold=0.000008,
            volume_multiplier=1.15,
            spread_threshold=0.00004,
            profit_target=0.0004,
            stop_loss=0.00025,
            enabled=self.config.get('sessions', {}).get('asian', {}).get('enabled', True)
        )
        
        # London Session (08:00 - 13:00 GMT)
        sessions[TradingSession.LONDON] = SessionConfig(
            name="London Session",
            start_time=time(8, 0),
            end_time=time(13, 0),
            liquidity="high",
            volatility="high",
            best_pairs=["EURUSDm", "GBPUSDm", "EURGBPm", "EURJPYm", "GBPJPYm", "XAUUSDm"],
            max_positions=5,
            risk_per_trade=0.01,   # 1%
            min_confidence=0.20,    # Lower confidence OK
            tick_threshold=0.000005,
            volume_multiplier=1.1,
            spread_threshold=0.00003,
            profit_target=0.0003,
            stop_loss=0.0002,
            enabled=self.config.get('sessions', {}).get('london', {}).get('enabled', True)
        )
        
        # London/NY Overlap (13:00 - 17:00 GMT) - BEST SESSION
        sessions[TradingSession.OVERLAP] = SessionConfig(
            name="London/NY Overlap",
            start_time=time(13, 0),
            end_time=time(17, 0),
            liquidity="very_high",
            volatility="high",
            best_pairs=["EURUSDm", "GBPUSDm", "USDJPYm", "USDCADm", "AUDUSDm", "XAUUSDm"],
            max_positions=8,
            risk_per_trade=0.015,  # 1.5% (can take more risk)
            min_confidence=0.15,    # Lowest confidence (many opportunities)
            tick_threshold=0.000003,
            volume_multiplier=1.05,
            spread_threshold=0.00002,
            profit_target=0.0002,
            stop_loss=0.00015,
            enabled=self.config.get('sessions', {}).get('overlap', {}).get('enabled', True)
        )
        
        # New York Session (17:00 - 22:00 GMT)
        sessions[TradingSession.NEW_YORK] = SessionConfig(
            name="New York Session",
            start_time=time(17, 0),
            end_time=time(22, 0),
            liquidity="high",
            volatility="medium",
            best_pairs=["EURUSDm", "GBPUSDm", "USDCADm", "USDJPYm", "XAUUSDm"],
            max_positions=5,
            risk_per_trade=0.01,   # 1%
            min_confidence=0.20,
            tick_threshold=0.000005,
            volume_multiplier=1.1,
            spread_threshold=0.00003,
            profit_target=0.0003,
            stop_loss=0.0002,
            enabled=self.config.get('sessions', {}).get('new_york', {}).get('enabled', True)
        )
        
        # Quiet Period (22:00 - 00:00 GMT)
        sessions[TradingSession.QUIET] = SessionConfig(
            name="Quiet Period",
            start_time=time(22, 0),
            end_time=time(23, 59),
            liquidity="low",
            volatility="low",
            best_pairs=["EURUSD", "GBPUSD"],
            max_positions=1,
            risk_per_trade=0.005,  # 0.5%
            min_confidence=0.40,    # Very high confidence needed
            tick_threshold=0.00001,
            volume_multiplier=1.3,
            spread_threshold=0.00005,
            profit_target=0.0005,
            stop_loss=0.0003,
            enabled=self.config.get('sessions', {}).get('quiet', {}).get('enabled', False)
        )
        
        return sessions
    
    def get_current_session(self) -> TradingSession:
        """Get current trading session based on GMT time.
        
        Returns:
            Current trading session
        """
        now = datetime.utcnow()
        current_time = now.time()
        day_of_week = now.weekday()  # 0=Monday, 6=Sunday
        
        # Check if market is closed (weekend)
        if day_of_week == 5:  # Saturday
            return TradingSession.CLOSED
        elif day_of_week == 6:  # Sunday
            # Market opens at 22:00 GMT on Sunday
            if current_time < time(22, 0):
                return TradingSession.CLOSED
        elif day_of_week == 4:  # Friday
            # Market closes at 22:00 GMT on Friday
            if current_time >= time(22, 0):
                return TradingSession.CLOSED
        
        # Determine session based on time
        if time(13, 0) <= current_time < time(17, 0):
            return TradingSession.OVERLAP
        elif time(8, 0) <= current_time < time(13, 0):
            return TradingSession.LONDON
        elif time(17, 0) <= current_time < time(22, 0):
            return TradingSession.NEW_YORK
        elif time(0, 0) <= current_time < time(8, 0):
            return TradingSession.ASIAN
        else:  # 22:00 - 00:00
            return TradingSession.QUIET
    
    def update_session(self) -> bool:
        """Update current session and return True if session changed.
        
        Returns:
            True if session changed, False otherwise
        """
        new_session = self.get_current_session()
        
        if new_session != self.current_session:
            old_session = self.current_session
            self.current_session = new_session
            
            if new_session == TradingSession.CLOSED:
                self.session_config = None
                logger.warning("⏸️  Market is CLOSED (Weekend)")
            else:
                self.session_config = self.sessions[new_session]
                logger.info(f"📊 Session changed: {old_session} → {new_session.value}")
                logger.info(f"   {self.session_config.name}")
                logger.info(f"   Liquidity: {self.session_config.liquidity}")
                logger.info(f"   Best pairs: {', '.join(self.session_config.best_pairs)}")
                logger.info(f"   Max positions: {self.session_config.max_positions}")
            
            return True
        
        return False
    
    def get_session_config(self) -> Optional[SessionConfig]:
        """Get configuration for current session.
        
        Returns:
            Session configuration or None if market closed
        """
        if self.current_session is None:
            self.update_session()
        
        return self.session_config
    
    def is_market_open(self) -> bool:
        """Check if market is currently open.
        
        Returns:
            True if market is open, False otherwise
        """
        if self.current_session is None:
            self.update_session()
        
        return self.current_session != TradingSession.CLOSED
    
    def should_trade_symbol(self, symbol: str) -> bool:
        """Check if symbol should be traded in current session.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if symbol is recommended for current session
        """
        if not self.is_market_open():
            return False
        
        if self.session_config is None:
            return False
        
        if not self.session_config.enabled:
            return False
        
        # Check if symbol is in best pairs for this session
        return symbol in self.session_config.best_pairs
    
    def get_hft_parameters(self) -> Dict[str, Any]:
        """Get HFT parameters for current session.
        
        Returns:
            Dictionary of HFT parameters
        """
        if self.session_config is None:
            # Return default conservative parameters if no session
            return {
                'tick_threshold': 0.00001,
                'volume_multiplier': 1.3,
                'mean_reversion_periods': 5,
                'profit_target': 0.0005,
                'stop_loss': 0.0003,
                'max_hold_time': 300,
                'min_confidence': 0.40,
                'price_momentum_threshold': 0.00002,
                'spread_threshold': 0.00005,
                'tick_imbalance_threshold': 0.6
            }
        
        return {
            'tick_threshold': self.session_config.tick_threshold,
            'volume_multiplier': self.session_config.volume_multiplier,
            'mean_reversion_periods': 5,
            'profit_target': self.session_config.profit_target,
            'stop_loss': self.session_config.stop_loss,
            'max_hold_time': 180,
            'min_confidence': self.session_config.min_confidence,
            'price_momentum_threshold': self.session_config.tick_threshold * 2,
            'spread_threshold': self.session_config.spread_threshold,
            'tick_imbalance_threshold': 0.5
        }
    
    def get_risk_parameters(self) -> Dict[str, float]:
        """Get risk parameters for current session.
        
        Returns:
            Dictionary of risk parameters
        """
        if self.session_config is None:
            return {
                'risk_per_trade': 0.005,
                'max_positions': 1
            }
        
        return {
            'risk_per_trade': self.session_config.risk_per_trade,
            'max_positions': self.session_config.max_positions
        }
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get information about current session.
        
        Returns:
            Dictionary with session information
        """
        if self.current_session is None:
            self.update_session()
        
        if self.current_session == TradingSession.CLOSED:
            return {
                'session': 'CLOSED',
                'name': 'Market Closed',
                'status': 'Weekend - Market is closed',
                'liquidity': 'none',
                'enabled': False
            }
        
        if self.session_config is None:
            return {
                'session': 'UNKNOWN',
                'name': 'Unknown',
                'status': 'Unable to determine session',
                'liquidity': 'unknown',
                'enabled': False
            }
        
        return {
            'session': self.current_session.value,
            'name': self.session_config.name,
            'status': 'Active' if self.session_config.enabled else 'Disabled',
            'liquidity': self.session_config.liquidity,
            'volatility': self.session_config.volatility,
            'best_pairs': self.session_config.best_pairs,
            'max_positions': self.session_config.max_positions,
            'risk_per_trade': self.session_config.risk_per_trade,
            'min_confidence': self.session_config.min_confidence,
            'enabled': self.session_config.enabled
        }
    
    def log_session_status(self) -> None:
        """Log current session status."""
        info = self.get_session_info()
        
        logger.info("=" * 60)
        logger.info("CURRENT TRADING SESSION")
        logger.info("-" * 60)
        logger.info(f"Session:      {info['name']}")
        logger.info(f"Status:       {info['status']}")
        logger.info(f"Liquidity:    {info.get('liquidity', 'N/A')}")
        
        if info['enabled']:
            logger.info(f"Best Pairs:   {', '.join(info.get('best_pairs', []))}")
            logger.info(f"Max Positions: {info.get('max_positions', 0)}")
            logger.info(f"Risk/Trade:   {info.get('risk_per_trade', 0):.2%}")
        
        logger.info("=" * 60)
