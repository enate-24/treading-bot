"""Tests for Configuration Manager."""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from trading_bot.configuration_manager import ConfigurationManager, ConfigurationError
from trading_bot.models.config import Environment


class TestConfigurationManager:
    """Test cases for Configuration Manager."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create Configuration Manager instance."""
        return ConfigurationManager(config_dir=temp_config_dir, environment=Environment.DEVELOPMENT)
    
    @pytest.fixture
    def valid_config(self):
        """Valid configuration for testing."""
        return {
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
                    "api_key": "test_key",
                    "api_secret": "test_secret",
                    "sandbox": True,
                    "rate_limit": 100,
                    "timeout": 30,
                    "priority": 1
                }
            },
            "environment": "development",
            "version": "1.0.0"
        }
    
    def test_initialization(self, temp_config_dir):
        """Test Configuration Manager initialization."""
        config_manager = ConfigurationManager(config_dir=temp_config_dir)
        
        assert config_manager.config_dir == Path(temp_config_dir)
        assert config_manager.environment == Environment.DEVELOPMENT
        assert config_manager.current_config == {}
        assert config_manager.config_history == []
        assert config_manager.version_counter == 0
    
    def test_create_default_config(self, config_manager):
        """Test default configuration creation."""
        default_config = config_manager.create_default_config()
        
        assert "trading" in default_config
        assert "exchanges" in default_config
        assert default_config["trading"]["strategy"] == "swing_trading"
        assert default_config["trading"]["risk_per_trade"] == 0.02
        assert len(default_config["trading"]["symbols"]) == 2
    
    def test_validate_configuration_valid(self, config_manager, valid_config):
        """Test configuration validation with valid config."""
        assert config_manager.validate_configuration(valid_config) is True
    
    def test_validate_configuration_invalid_risk(self, config_manager, valid_config):
        """Test configuration validation with invalid risk per trade."""
        valid_config["trading"]["risk_per_trade"] = 0.1  # 10% - too high
        assert config_manager.validate_configuration(valid_config) is False
    
    def test_validate_configuration_invalid_strategy(self, config_manager, valid_config):
        """Test configuration validation with invalid strategy."""
        valid_config["trading"]["strategy"] = "invalid_strategy"
        assert config_manager.validate_configuration(valid_config) is False
    
    def test_validate_configuration_invalid_timeframe(self, config_manager, valid_config):
        """Test configuration validation with invalid timeframe."""
        valid_config["trading"]["timeframes"] = ["1h", "invalid_timeframe"]
        assert config_manager.validate_configuration(valid_config) is False
    
    def test_validate_configuration_missing_exchange_fields(self, config_manager, valid_config):
        """Test configuration validation with missing exchange fields."""
        del valid_config["exchanges"]["binance"]["api_key"]
        assert config_manager.validate_configuration(valid_config) is False
    
    def test_save_and_load_configuration(self, config_manager, valid_config):
        """Test saving and loading configuration."""
        config_file = "test_config.json"
        
        # Save configuration
        config_manager.save_configuration(valid_config, config_file)
        
        # Load configuration
        loaded_config = config_manager.load_configuration(config_file)
        
        # Verify loaded configuration matches original (excluding encrypted fields)
        assert loaded_config["trading"] == valid_config["trading"]
        assert loaded_config["environment"] == valid_config["environment"]
        assert loaded_config["version"] == valid_config["version"]
    
    def test_load_nonexistent_configuration(self, config_manager):
        """Test loading non-existent configuration file."""
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            config_manager.load_configuration("nonexistent.json")
    
    def test_update_configuration(self, config_manager, valid_config):
        """Test configuration updates."""
        # Set initial configuration
        config_manager.current_config = valid_config
        
        # Update configuration
        updates = {
            "trading": {
                "risk_per_trade": 0.015,
                "symbols": ["BTC/USDT", "ETH/USDT", "ADA/USDT"]
            }
        }
        
        config_manager.update_configuration(updates)
        
        # Verify updates were applied
        assert config_manager.current_config["trading"]["risk_per_trade"] == 0.015
        assert len(config_manager.current_config["trading"]["symbols"]) == 3
        assert "ADA/USDT" in config_manager.current_config["trading"]["symbols"]
        
        # Verify other fields remain unchanged
        assert config_manager.current_config["trading"]["strategy"] == "swing_trading"
    
    def test_update_configuration_invalid(self, config_manager, valid_config):
        """Test updating configuration with invalid values."""
        config_manager.current_config = valid_config
        
        # Try to update with invalid risk
        updates = {
            "trading": {
                "risk_per_trade": 0.1  # 10% - too high
            }
        }
        
        with pytest.raises(ConfigurationError, match="Updated configuration is invalid"):
            config_manager.update_configuration(updates)
    
    def test_configuration_history(self, config_manager, valid_config):
        """Test configuration history tracking."""
        # Load initial configuration
        config_manager.current_config = valid_config
        config_manager._add_to_history(valid_config, "Initial load")
        
        # Update configuration
        updates = {"trading": {"risk_per_trade": 0.015}}
        config_manager.update_configuration(updates)
        
        # Check history
        history = config_manager.get_configuration_history()
        assert len(history) >= 2  # Initial + before update
        
        # Verify history structure
        for entry in history:
            assert "version" in entry
            assert "timestamp" in entry
            assert "description" in entry
            assert "environment" in entry
            assert "config" in entry
    
    def test_rollback_configuration(self, config_manager, valid_config):
        """Test configuration rollback."""
        # Set initial configuration
        config_manager.current_config = valid_config
        config_manager._add_to_history(valid_config, "Initial")
        
        # Update configuration
        updates = {"trading": {"risk_per_trade": 0.015}}
        config_manager.update_configuration(updates)
        
        # Verify update was applied
        assert config_manager.current_config["trading"]["risk_per_trade"] == 0.015
        
        # Rollback to version 1
        config_manager.rollback_configuration(1)
        
        # Verify rollback
        assert config_manager.current_config["trading"]["risk_per_trade"] == 0.02
    
    def test_rollback_nonexistent_version(self, config_manager):
        """Test rollback to non-existent version."""
        with pytest.raises(ConfigurationError, match="Configuration version 999 not found"):
            config_manager.rollback_configuration(999)
    
    def test_encryption_decryption(self, config_manager):
        """Test encryption and decryption of sensitive data."""
        config_with_secrets = {
            "exchanges": {
                "binance": {
                    "api_key": "secret_key_123",
                    "api_secret": "secret_value_456",
                    "name": "binance"
                }
            }
        }
        
        # Encrypt
        encrypted = config_manager._encrypt_sensitive_data(config_with_secrets)
        
        # Verify sensitive data is encrypted (different from original)
        assert encrypted["exchanges"]["binance"]["api_key"] != "secret_key_123"
        assert encrypted["exchanges"]["binance"]["api_secret"] != "secret_value_456"
        
        # Verify non-sensitive data is unchanged
        assert encrypted["exchanges"]["binance"]["name"] == "binance"
        
        # Decrypt
        decrypted = config_manager._decrypt_sensitive_data(encrypted)
        
        # Verify decryption restores original values
        assert decrypted["exchanges"]["binance"]["api_key"] == "secret_key_123"
        assert decrypted["exchanges"]["binance"]["api_secret"] == "secret_value_456"
        assert decrypted["exchanges"]["binance"]["name"] == "binance"
    
    def test_get_current_config(self, config_manager, valid_config):
        """Test getting current configuration."""
        config_manager.current_config = valid_config
        
        current = config_manager.get_current_config()
        
        # Verify it's a deep copy
        assert current == valid_config
        assert current is not valid_config
        
        # Modify returned config shouldn't affect original
        current["trading"]["risk_per_trade"] = 0.1
        assert config_manager.current_config["trading"]["risk_per_trade"] == 0.02
    
    def test_environment_specific_config(self, temp_config_dir):
        """Test environment-specific configuration handling."""
        # Create managers for different environments
        dev_manager = ConfigurationManager(config_dir=temp_config_dir, environment=Environment.DEVELOPMENT)
        prod_manager = ConfigurationManager(config_dir=temp_config_dir, environment=Environment.PRODUCTION)
        
        assert dev_manager.environment == Environment.DEVELOPMENT
        assert prod_manager.environment == Environment.PRODUCTION
        
        # Verify they use different environments in history
        dev_config = {"test": "dev_value"}
        prod_config = {"test": "prod_value"}
        
        dev_manager._add_to_history(dev_config, "Dev config")
        prod_manager._add_to_history(prod_config, "Prod config")
        
        dev_history = dev_manager.get_configuration_history()
        prod_history = prod_manager.get_configuration_history()
        
        assert dev_history[0]["environment"] == "development"
        assert prod_history[0]["environment"] == "production"
    
    def test_constraints_validation(self, config_manager):
        """Test configuration constraints validation."""
        constraints = config_manager.constraints
        
        # Test risk per trade constraints
        assert constraints.min_risk_per_trade == 0.001
        assert constraints.max_risk_per_trade == 0.05
        
        # Test supported strategies
        assert "scalping" in constraints.supported_strategies
        assert "swing_trading" in constraints.supported_strategies
        
        # Test supported timeframes
        assert "1m" in constraints.supported_timeframes
        assert "1h" in constraints.supported_timeframes
        assert "1d" in constraints.supported_timeframes
    
    def test_invalid_json_file(self, config_manager, temp_config_dir):
        """Test loading invalid JSON configuration file."""
        # Create invalid JSON file
        invalid_json_file = Path(temp_config_dir) / "invalid.json"
        with open(invalid_json_file, 'w') as f:
            f.write("{ invalid json content")
        
        with pytest.raises(ConfigurationError, match="Invalid JSON in configuration file"):
            config_manager.load_configuration("invalid.json")
    
    def test_history_size_limit(self, config_manager, valid_config):
        """Test configuration history size limit."""
        config_manager.current_config = valid_config
        
        # Add more than 50 versions to history
        for i in range(55):
            config_manager._add_to_history(valid_config, f"Version {i}")
        
        # Verify history is limited to 50 entries
        assert len(config_manager.config_history) == 50
        
        # Verify it keeps the most recent entries
        history = config_manager.get_configuration_history()
        assert "Version 54" in history[-1]["description"]