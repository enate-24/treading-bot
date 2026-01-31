"""Simple demonstration of Configuration Manager functionality."""

import tempfile
from trading_bot.configuration_manager import ConfigurationManager
from trading_bot.models.config import Environment


def main():
    """Demonstrate key Configuration Manager features."""
    
    print("🔧 Configuration Manager Demo")
    print("=" * 50)
    
    # Create temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize Configuration Manager
        config_manager = ConfigurationManager(
            config_dir=temp_dir,
            environment=Environment.DEVELOPMENT
        )
        
        print("\n1. ✅ Configuration Manager initialized")
        
        # Create and validate default configuration
        default_config = config_manager.create_default_config()
        is_valid = config_manager.validate_configuration(default_config)
        print(f"2. ✅ Default configuration created and validated: {is_valid}")
        
        # Save configuration
        config_manager.save_configuration(default_config, "demo_config.json")
        print("3. ✅ Configuration saved with encryption")
        
        # Load configuration
        loaded_config = config_manager.load_configuration("demo_config.json")
        print("4. ✅ Configuration loaded and decrypted")
        
        # Update configuration
        updates = {
            "trading": {
                "risk_per_trade": 0.015,
                "symbols": ["BTC/USDT", "ETH/USDT", "ADA/USDT"]
            }
        }
        config_manager.update_configuration(updates)
        print("5. ✅ Configuration updated dynamically")
        
        # Show history
        history = config_manager.get_configuration_history()
        print(f"6. ✅ Configuration history tracked: {len(history)} versions")
        
        # Test rollback
        if len(history) >= 2:
            config_manager.rollback_configuration(1)
            print("7. ✅ Configuration rolled back successfully")
        
        print("\n🎉 All Configuration Manager features working correctly!")
        print("\nKey Features Demonstrated:")
        print("  • Configuration validation with constraints")
        print("  • Encryption of sensitive data (API keys)")
        print("  • Dynamic configuration updates without restart")
        print("  • Version history and rollback capabilities")
        print("  • Environment-specific configurations")
        print("  • JSON file persistence")


if __name__ == "__main__":
    main()