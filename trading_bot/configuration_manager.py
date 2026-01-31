"""Configuration Manager implementation for system configuration management."""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from cryptography.fernet import Fernet
import copy

from .interfaces.configuration_manager import IConfigurationManager
from .models.config import (
    Environment,
    TradingConfig,
    ExchangeConfig,
    ConfigurationVersion,
    ConfigurationConstraints
)


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors."""
    pass


class ConfigurationManager(IConfigurationManager):
    """Configuration Manager with validation, versioning, and encryption."""
    
    def __init__(self, config_dir: str = "config", environment: Environment = Environment.DEVELOPMENT):
        """Initialize Configuration Manager.
        
        Args:
            config_dir: Directory to store configuration files
            environment: Current environment (development, staging, production)
        """
        self.logger = logging.getLogger(__name__)
        self.config_dir = Path(config_dir)
        self.environment = environment
        self.constraints = ConfigurationConstraints()
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(exist_ok=True)
        
        # Configuration storage
        self.current_config: Dict[str, Any] = {}
        self.config_history: List[ConfigurationVersion] = []
        self.version_counter = 0
        
        # Encryption key for sensitive data
        self._encryption_key = self._load_or_create_encryption_key()
        self._cipher = Fernet(self._encryption_key)
        
        # Sensitive configuration keys that should be encrypted
        self.sensitive_keys = {
            'api_key', 'api_secret', 'password', 'token', 'secret'
        }
        
        self.logger.info(f"Configuration Manager initialized for {environment.value} environment")
    
    def _load_or_create_encryption_key(self) -> bytes:
        """Load existing encryption key or create a new one."""
        key_file = self.config_dir / ".encryption_key"
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            return key
    
    def _encrypt_sensitive_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive configuration data."""
        encrypted_config = copy.deepcopy(config)
        
        def encrypt_recursive(obj: Any, path: str = "") -> Any:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if any(sensitive in key.lower() for sensitive in self.sensitive_keys):
                        if isinstance(value, str):
                            obj[key] = self._cipher.encrypt(value.encode()).decode()
                            self.logger.debug(f"Encrypted sensitive field: {current_path}")
                    elif isinstance(value, (dict, list)):
                        encrypt_recursive(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    encrypt_recursive(item, f"{path}[{i}]")
            return obj
        
        return encrypt_recursive(encrypted_config)
    
    def _decrypt_sensitive_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive configuration data."""
        decrypted_config = copy.deepcopy(config)
        
        def decrypt_recursive(obj: Any, path: str = "") -> Any:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if any(sensitive in key.lower() for sensitive in self.sensitive_keys):
                        if isinstance(value, str):
                            try:
                                obj[key] = self._cipher.decrypt(value.encode()).decode()
                                self.logger.debug(f"Decrypted sensitive field: {current_path}")
                            except Exception as e:
                                self.logger.warning(f"Failed to decrypt {current_path}: {e}")
                    elif isinstance(value, (dict, list)):
                        decrypt_recursive(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    decrypt_recursive(item, f"{path}[{i}]")
            return obj
        
        return decrypt_recursive(decrypted_config)
    
    def load_configuration(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigurationError: If configuration file cannot be loaded or is invalid
        """
        try:
            full_path = self.config_dir / config_path
            
            if not full_path.exists():
                raise ConfigurationError(f"Configuration file not found: {full_path}")
            
            with open(full_path, 'r') as f:
                config = json.load(f)
            
            # Decrypt sensitive data
            config = self._decrypt_sensitive_data(config)
            
            # Validate configuration
            if not self.validate_configuration(config):
                raise ConfigurationError("Configuration validation failed")
            
            # Store as current configuration
            self.current_config = config
            
            # Add to history
            self._add_to_history(config, f"Loaded from {config_path}")
            
            self.logger.info(f"Configuration loaded successfully from {config_path}")
            return config
            
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    def save_configuration(self, config: Dict[str, Any], config_path: str) -> None:
        """Save configuration to file.
        
        Args:
            config: Configuration dictionary to save
            config_path: Path to save configuration file
        """
        try:
            # Validate before saving
            if not self.validate_configuration(config):
                raise ConfigurationError("Cannot save invalid configuration")
            
            # Encrypt sensitive data for storage
            encrypted_config = self._encrypt_sensitive_data(config)
            
            full_path = self.config_dir / config_path
            
            with open(full_path, 'w') as f:
                json.dump(encrypted_config, f, indent=2, default=str)
            
            self.logger.info(f"Configuration saved to {config_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")
    
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate configuration parameters.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if configuration is valid
        """
        try:
            # Validate trading configuration
            if 'trading' in config:
                trading_config = config['trading']
                
                # Validate risk per trade
                risk_per_trade = trading_config.get('risk_per_trade', 0)
                if not (self.constraints.min_risk_per_trade <= risk_per_trade <= self.constraints.max_risk_per_trade):
                    self.logger.error(f"Invalid risk_per_trade: {risk_per_trade}. Must be between {self.constraints.min_risk_per_trade} and {self.constraints.max_risk_per_trade}")
                    return False
                
                # Validate max drawdown
                max_drawdown = trading_config.get('max_drawdown', 0)
                if not (self.constraints.min_max_drawdown <= max_drawdown <= self.constraints.max_max_drawdown):
                    self.logger.error(f"Invalid max_drawdown: {max_drawdown}. Must be between {self.constraints.min_max_drawdown} and {self.constraints.max_max_drawdown}")
                    return False
                
                # Validate daily loss limit
                daily_loss_limit = trading_config.get('daily_loss_limit', 0)
                if not (self.constraints.min_daily_loss_limit <= daily_loss_limit <= self.constraints.max_daily_loss_limit):
                    self.logger.error(f"Invalid daily_loss_limit: {daily_loss_limit}. Must be between {self.constraints.min_daily_loss_limit} and {self.constraints.max_daily_loss_limit}")
                    return False
                
                # Validate strategy
                strategy = trading_config.get('strategy', '')
                if strategy not in self.constraints.supported_strategies:
                    self.logger.error(f"Invalid strategy: {strategy}. Must be one of {self.constraints.supported_strategies}")
                    return False
                
                # Validate timeframes
                timeframes = trading_config.get('timeframes', [])
                for timeframe in timeframes:
                    if timeframe not in self.constraints.supported_timeframes:
                        self.logger.error(f"Invalid timeframe: {timeframe}. Must be one of {self.constraints.supported_timeframes}")
                        return False
                
                # Validate symbols count
                symbols = trading_config.get('symbols', [])
                if len(symbols) > self.constraints.max_symbols:
                    self.logger.error(f"Too many symbols: {len(symbols)}. Maximum allowed: {self.constraints.max_symbols}")
                    return False
            
            # Validate exchange configurations
            if 'exchanges' in config:
                exchanges = config['exchanges']
                for exchange_name, exchange_config in exchanges.items():
                    # Validate rate limit
                    rate_limit = exchange_config.get('rate_limit', 0)
                    if not (self.constraints.min_rate_limit <= rate_limit <= self.constraints.max_rate_limit):
                        self.logger.error(f"Invalid rate_limit for {exchange_name}: {rate_limit}")
                        return False
                    
                    # Validate timeout
                    timeout = exchange_config.get('timeout', 0)
                    if not (self.constraints.min_timeout <= timeout <= self.constraints.max_timeout):
                        self.logger.error(f"Invalid timeout for {exchange_name}: {timeout}")
                        return False
                    
                    # Validate required fields
                    required_fields = ['name', 'api_key', 'api_secret']
                    for field in required_fields:
                        if field not in exchange_config or not exchange_config[field]:
                            self.logger.error(f"Missing required field '{field}' for exchange {exchange_name}")
                            return False
            
            self.logger.debug("Configuration validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration validation error: {e}")
            return False
    
    def update_configuration(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values.
        
        Args:
            updates: Dictionary of configuration updates
        """
        try:
            # Create updated configuration
            updated_config = copy.deepcopy(self.current_config)
            
            # Apply updates recursively
            def apply_updates(target: Dict[str, Any], source: Dict[str, Any]) -> None:
                for key, value in source.items():
                    if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                        apply_updates(target[key], value)
                    else:
                        target[key] = value
            
            apply_updates(updated_config, updates)
            
            # Validate updated configuration
            if not self.validate_configuration(updated_config):
                raise ConfigurationError("Updated configuration is invalid")
            
            # Store previous configuration in history
            self._add_to_history(self.current_config, "Before update")
            
            # Apply updates
            self.current_config = updated_config
            
            # Save updated configuration
            config_file = f"{self.environment.value}_config.json"
            self.save_configuration(self.current_config, config_file)
            
            self.logger.info("Configuration updated successfully")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to update configuration: {e}")
    
    def get_configuration_history(self) -> List[Dict[str, Any]]:
        """Get configuration change history.
        
        Returns:
            List of historical configurations
        """
        return [
            {
                'version': version.version,
                'timestamp': version.timestamp.isoformat(),
                'description': version.description,
                'environment': version.environment.value,
                'config': version.config
            }
            for version in self.config_history
        ]
    
    def rollback_configuration(self, version: int) -> None:
        """Rollback to previous configuration version.
        
        Args:
            version: Configuration version to rollback to
        """
        try:
            # Find the version
            target_version = None
            for config_version in self.config_history:
                if config_version.version == version:
                    target_version = config_version
                    break
            
            if target_version is None:
                raise ConfigurationError(f"Configuration version {version} not found")
            
            # Validate the historical configuration
            if not self.validate_configuration(target_version.config):
                raise ConfigurationError(f"Historical configuration version {version} is no longer valid")
            
            # Store current configuration in history before rollback
            self._add_to_history(self.current_config, f"Before rollback to version {version}")
            
            # Apply rollback
            self.current_config = copy.deepcopy(target_version.config)
            
            # Save rolled back configuration
            config_file = f"{self.environment.value}_config.json"
            self.save_configuration(self.current_config, config_file)
            
            self.logger.info(f"Configuration rolled back to version {version}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to rollback configuration: {e}")
    
    def _add_to_history(self, config: Dict[str, Any], description: str) -> None:
        """Add configuration to history."""
        self.version_counter += 1
        version = ConfigurationVersion(
            version=self.version_counter,
            config=copy.deepcopy(config),
            timestamp=datetime.now(),
            description=description,
            environment=self.environment
        )
        self.config_history.append(version)
        
        # Keep only last 50 versions to prevent unlimited growth
        if len(self.config_history) > 50:
            self.config_history = self.config_history[-50:]
    
    def get_current_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return copy.deepcopy(self.current_config)
    
    def create_default_config(self) -> Dict[str, Any]:
        """Create a default configuration."""
        default_config = {
            "trading": {
                "symbols": ["BTC/USDT", "ETH/USDT"],
                "timeframes": ["1h", "4h"],
                "strategy": "swing_trading",
                "risk_per_trade": 0.02,
                "max_drawdown": 0.15,
                "daily_loss_limit": 0.05
            },
            "exchanges": {
                "binance": {
                    "name": "binance",
                    "api_key": "your_api_key_here",
                    "api_secret": "your_api_secret_here",
                    "sandbox": True,
                    "rate_limit": 100,
                    "timeout": 30,
                    "priority": 1
                }
            },
            "environment": self.environment.value,
            "version": "1.0.0"
        }
        
        return default_config