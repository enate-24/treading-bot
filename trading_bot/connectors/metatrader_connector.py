"""MetaTrader 4/5 connector for forex and CFD trading."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logging.warning("MetaTrader5 package not installed. Install with: pip install MetaTrader5")


class MTTimeframe(Enum):
    """MetaTrader timeframe mappings."""
    M1 = 1      # 1 minute
    M5 = 5      # 5 minutes
    M15 = 15    # 15 minutes
    M30 = 30    # 30 minutes
    H1 = 60     # 1 hour
    H4 = 240    # 4 hours
    D1 = 1440   # 1 day
    W1 = 10080  # 1 week
    MN1 = 43200 # 1 month


class MetaTraderConnector:
    """Connector for MetaTrader 4/5 platforms."""
    
    def __init__(self, account: int, password: str, server: str, mt_version: int = 5):
        """Initialize MetaTrader connector.
        
        Args:
            account: Trading account number
            password: Trading account password
            server: Broker server name
            mt_version: MetaTrader version (4 or 5)
        """
        if not MT5_AVAILABLE:
            raise ImportError(
                "MetaTrader5 package is required. Install with: pip install MetaTrader5"
            )
        
        self.logger = logging.getLogger(__name__)
        self.account = account
        self.password = password
        self.server = server
        self.mt_version = mt_version
        self.connected = False
        
        if mt_version != 5:
            self.logger.warning("Only MT5 is fully supported via MetaTrader5 package")
    
    def connect(self) -> bool:
        """Connect to MetaTrader terminal.
        
        Returns:
            True if connection successful
        """
        try:
            # Initialize MT5 connection
            if not mt5.initialize():
                error = mt5.last_error()
                self.logger.error(f"MT5 initialization failed: {error}")
                
                # Provide helpful error messages
                if error[0] == -10005:
                    self.logger.error("MetaTrader 5 terminal is not running!")
                    self.logger.error("Please start MetaTrader 5 and try again.")
                elif error[0] == -6:
                    self.logger.error("Authorization failed!")
                    self.logger.error("Please check:")
                    self.logger.error("  1. MetaTrader 5 is logged into your account")
                    self.logger.error("  2. Account credentials in config are correct")
                    self.logger.error("  3. Try logging in manually in MT5 first")
                
                return False
            
            self.logger.info("MT5 initialized successfully")
            
            # Check if already logged in to the correct account
            account_info = mt5.account_info()
            if account_info and account_info.login == self.account:
                self.logger.info(f"Already logged in to account: {self.account}")
                self.connected = True
                self.logger.info(f"Balance: {account_info.balance} {account_info.currency}")
                return True
            
            # Try to login to trading account
            self.logger.info(f"Attempting to login to account: {self.account}")
            self.logger.info(f"Server: {self.server}")
            
            authorized = mt5.login(
                login=self.account,
                password=self.password,
                server=self.server
            )
            
            if not authorized:
                error = mt5.last_error()
                self.logger.error(f"MT5 login failed: {error}")
                self.logger.error("Please check:")
                self.logger.error(f"  1. Account number: {self.account}")
                self.logger.error(f"  2. Server name: {self.server}")
                self.logger.error("  3. Password is correct")
                self.logger.error("  4. Account is active and not expired")
                self.logger.error("  5. Try logging in manually in MT5 terminal first")
                mt5.shutdown()
                return False
            
            self.connected = True
            account_info = mt5.account_info()
            self.logger.info(f"Connected to MT5 account: {account_info.login}")
            self.logger.info(f"Balance: {account_info.balance} {account_info.currency}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from MetaTrader terminal."""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            self.logger.info("Disconnected from MT5")
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information.
        
        Returns:
            Dictionary with account details
        """
        if not self.connected:
            self.logger.error("Not connected to MT5")
            return None
        
        try:
            account_info = mt5.account_info()
            if account_info is None:
                return None
            
            return {
                'login': account_info.login,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'free_margin': account_info.margin_free,
                'margin_level': account_info.margin_level,
                'profit': account_info.profit,
                'currency': account_info.currency,
                'leverage': account_info.leverage,
                'server': account_info.server,
                'company': account_info.company
            }
        except Exception as e:
            self.logger.error(f"Error getting account info: {e}")
            return None
    
    def get_symbols(self) -> List[str]:
        """Get available trading symbols.
        
        Returns:
            List of symbol names
        """
        if not self.connected:
            self.logger.error("Not connected to MT5")
            return []
        
        try:
            symbols = mt5.symbols_get()
            return [symbol.name for symbol in symbols if symbol.visible]
        except Exception as e:
            self.logger.error(f"Error getting symbols: {e}")
            return []
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information.
        
        Args:
            symbol: Symbol name (e.g., 'EURUSD', 'GBPUSD')
            
        Returns:
            Dictionary with symbol details
        """
        if not self.connected:
            self.logger.error("Not connected to MT5")
            return None
        
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return None
            
            return {
                'name': symbol_info.name,
                'description': symbol_info.description,
                'point': symbol_info.point,
                'digits': symbol_info.digits,
                'spread': symbol_info.spread,
                'trade_contract_size': symbol_info.trade_contract_size,
                'volume_min': symbol_info.volume_min,
                'volume_max': symbol_info.volume_max,
                'volume_step': symbol_info.volume_step,
                'bid': symbol_info.bid,
                'ask': symbol_info.ask
            }
        except Exception as e:
            self.logger.error(f"Error getting symbol info: {e}")
            return None
    
    def get_market_data(self, symbol: str, timeframe: str, bars: int = 100) -> Optional[List[Dict]]:
        """Get historical market data.
        
        Args:
            symbol: Symbol name
            timeframe: Timeframe (M1, M5, M15, M30, H1, H4, D1, W1, MN1)
            bars: Number of bars to retrieve
            
        Returns:
            List of OHLCV data dictionaries
        """
        if not self.connected:
            self.logger.error("Not connected to MT5")
            return None
        
        try:
            # Map timeframe string to MT5 constant
            tf_map = {
                'M1': mt5.TIMEFRAME_M1,
                'M5': mt5.TIMEFRAME_M5,
                'M15': mt5.TIMEFRAME_M15,
                'M30': mt5.TIMEFRAME_M30,
                'H1': mt5.TIMEFRAME_H1,
                'H4': mt5.TIMEFRAME_H4,
                'D1': mt5.TIMEFRAME_D1,
                'W1': mt5.TIMEFRAME_W1,
                'MN1': mt5.TIMEFRAME_MN1
            }
            
            mt_timeframe = tf_map.get(timeframe.upper())
            if mt_timeframe is None:
                self.logger.error(f"Invalid timeframe: {timeframe}")
                return None
            
            # Get rates
            rates = mt5.copy_rates_from_pos(symbol, mt_timeframe, 0, bars)
            if rates is None or len(rates) == 0:
                return None
            
            # Convert to list of dictionaries
            data = []
            for rate in rates:
                data.append({
                    'timestamp': datetime.fromtimestamp(rate['time']),
                    'open': rate['open'],
                    'high': rate['high'],
                    'low': rate['low'],
                    'close': rate['close'],
                    'volume': rate['tick_volume']
                })
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error getting market data: {e}")
            return None
    
    def place_order(self, symbol: str, order_type: str, volume: float, 
                   price: Optional[float] = None, sl: Optional[float] = None, 
                   tp: Optional[float] = None, comment: str = "") -> Optional[Dict]:
        """Place a trading order.
        
        Args:
            symbol: Symbol name
            order_type: 'BUY' or 'SELL'
            volume: Order volume (lots)
            price: Order price (None for market orders)
            sl: Stop loss price
            tp: Take profit price
            comment: Order comment
            
        Returns:
            Order result dictionary
        """
        if not self.connected:
            self.logger.error("Not connected to MT5")
            return None
        
        try:
            # Prepare order request
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                self.logger.error(f"Symbol {symbol} not found")
                return None
            
            # Determine order type
            if order_type.upper() == 'BUY':
                trade_type = mt5.ORDER_TYPE_BUY
                price = price or mt5.symbol_info_tick(symbol).ask
            elif order_type.upper() == 'SELL':
                trade_type = mt5.ORDER_TYPE_SELL
                price = price or mt5.symbol_info_tick(symbol).bid
            else:
                self.logger.error(f"Invalid order type: {order_type}")
                return None
            
            # Create order request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": trade_type,
                "price": price,
                "deviation": 20,
                "magic": 234000,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Add stop loss and take profit if provided
            if sl is not None:
                request["sl"] = sl
            if tp is not None:
                request["tp"] = tp
            
            # Send order
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Order failed: {result.comment}")
                return None
            
            self.logger.info(f"Order placed: {order_type} {volume} {symbol} @ {price}")
            
            return {
                'order_id': result.order,
                'volume': result.volume,
                'price': result.price,
                'comment': result.comment,
                'retcode': result.retcode
            }
            
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return None
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get open positions.
        
        Returns:
            List of position dictionaries
        """
        if not self.connected:
            self.logger.error("Not connected to MT5")
            return []
        
        try:
            positions = mt5.positions_get()
            if positions is None:
                return []
            
            result = []
            for pos in positions:
                result.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL',
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'price_current': pos.price_current,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'profit': pos.profit,
                    'comment': pos.comment
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []
    
    def close_position(self, ticket: int) -> bool:
        """Close an open position.
        
        Args:
            ticket: Position ticket number
            
        Returns:
            True if position closed successfully
        """
        if not self.connected:
            self.logger.error("Not connected to MT5")
            return False
        
        try:
            position = mt5.positions_get(ticket=ticket)
            if position is None or len(position) == 0:
                self.logger.error(f"Position {ticket} not found")
                return False
            
            pos = position[0]
            
            # Determine close order type (opposite of position type)
            if pos.type == mt5.ORDER_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
                price = mt5.symbol_info_tick(pos.symbol).bid
            else:
                order_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(pos.symbol).ask
            
            # Create close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": 234000,
                "comment": "Close position",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Failed to close position: {result.comment}")
                return False
            
            self.logger.info(f"Position {ticket} closed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
