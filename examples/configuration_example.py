"""Example demonstrating Configuration Manager usage."""

import os
import tempfile
from pathlib import Path

from trading_bot.configuration_manager import ConfigurationManager
from trading_bot.models.config import Environment


def main():
    """Demonstrate Configuration Manager functionality."""
    
    # Create temporary directory for this example
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary config directory: {temp_dir}")
        
        # Initialize Configuration Manager
        config_manager = ConfigurationManager(
            config_dir=temp_dir,
            environment=Environment.DEVELOPMENT
        )
        
        print("\n1. Creating default configuration...")
        default_config = config_manager.create_default_config()
        print(f"Default strategy: {default_config['trading']['strategy']}")
        print(f"Default risk per trade: {default_config['trading']['risk_per_trade']}")
        print(f"Default symbols: {default_config['trading']['symbols']}")
        
        # Save the default configuration
        config_manager.save_configuration(default_config, "default_config.json")
        print("✓ Default configuration saved")
        
        # Load the configuration
        print("\n2. Loading configuration...")
        loaded_config = config_manager.load_configuration("default_config.json")
        print(f"Loaded strategy: {loaded_config['trading']['strategy']}")
        print("✓ Configuration loaded successfully")
        
        # Update configuration
        print("\n3. Updating configuration...")
        updates = {
            "trading": {
                "risk_per_trade": 0.015,  # Reduce risk to 1.5%
                "symbols": ["BTC/USDT", "ETH/USDT", "ADA/USDT"],  # Add ADA
                "strategy": "scalping"  # Change to scalping
            }
        }
        
        config_manager.update_configuration(updates)
        print(f"Updated risk per trade: {config_manager.current_config['trading']['risk_per_trade']}")
        print(f"Updated strategy: {config_manager.current_config['trading']['strategy']}")
        print(f"Updated symbols: {config_manager.current_config['trading']['symbols']}")
        print("✓ Configuration updated successfully")
        
        # Show configuration history
        print("\n4. Configuration history...")
        history = config_manager.get_configuration_history()
        for entry in history:
            print(f"Version {entry['version']}: {entry['description']} at {entry['timestamp']}")
        
        # Rollback configuration
        print("\n5. Rolling back configuration...")
        if len(history) >= 2:
            config_manager.rollback_configuration(1)  # Rollback to first version
            print(f"After rollback - strategy: {config_manager.current_config['trading']['strategy']}")
            print(f"After rollback - risk: {config_manager.current_config['trading']['risk_per_trade']}")
            print("✓ Configuration rolled back successfully")
        
        # Demonstrate validation
        print("\n6. Testing configuration validation...")
        
        # Valid configuration
        valid_test_config = {
            "trading": {
                "symbols": ["BTC/USDT"],
                "timeframes": ["1h"],
                "strategy": "swing_trading",
                "risk_per_trade": 0.02,
                "max_drawdown": 0.15,
                "daily_loss_limit": 0.05
            }
        }
        
        is_valid = config_manager.validate_configuration(valid_test_config)
        print(f"Valid config validation result: {is_valid}")
        
        # Invalid configuration (risk too high)
        invalid_test_config = {
            "trading": {
                "symbols": ["BTC/USDT"],
                "timeframes": ["1h"],
                "strategy": "swing_trading",
                "risk_per_trade": 0.1,  # 10% - too high!
                "max_drawdown": 0.15,
                "daily_loss_limit": 0.05
            }
        }
        
        is_valid = config_manager.validate_configuration(invalid_test_config)
        print(f"Invalid config validation result: {is_valid}")
        
        # Show encryption in action
        print("\n7. Demonstrating encryption...")
        config_with_secrets = {
            "exchanges": {
                "binance": {
                    "name": "binance",
                    "api_key": "my_secret_api_key_123",
                    "api_secret": "my_secret_value_456"
                }
            }
        }
        
        print(f"Original API key: {config_with_secrets['exchanges']['binance']['api_key']}")
        
        # Encrypt
        encrypted = config_manager._encrypt_sensitive_data(config_with_secrets)
        print(f"Encrypted API key: {encrypted['exchanges']['binance']['api_key'][:50]}...")
        
        # Decrypt
        decrypted = config_manager._decrypt_sensitive_data(encrypted)
        print(f"Decrypted API key: {decrypted['exchanges']['binance']['api_key']}")
        print("✓ Encryption/decryption working correctly")
        
        print("\n✅ Configuration Manager example completed successfully!")


if __name__ == "__main__":
    main()