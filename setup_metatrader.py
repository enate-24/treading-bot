"""Setup script for MetaTrader integration."""

import json
from pathlib import Path


def setup_metatrader_config():
    """Create MetaTrader configuration template."""
    
    print("🔧 MetaTrader Integration Setup")
    print("=" * 50)
    
    # Create config directory
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    # MetaTrader configuration template
    mt_config = {
        "metatrader": {
            "account": 12345678,
            "password": "your_password_here",
            "server": "YourBroker-Demo",
            "version": 5,
            "enabled": True
        },
        "trading": {
            "symbols": ["EURUSD", "GBPUSD", "USDJPY"],
            "timeframes": ["H1", "H4"],
            "strategy": "swing_trading",
            "risk_per_trade": 0.01,
            "max_drawdown": 0.10,
            "daily_loss_limit": 0.03
        },
        "environment": "production",
        "version": "1.0.0"
    }
    
    # Save configuration
    config_file = config_dir / "metatrader_config.json"
    with open(config_file, 'w') as f:
        json.dump(mt_config, f, indent=2)
    
    print(f"✅ Configuration template created: {config_file}")
    print("\n📝 Next steps:")
    print("  1. Install MetaTrader5 package:")
    print("     pip install MetaTrader5")
    print("\n  2. Make sure MetaTrader 5 terminal is installed and running")
    print("     Download from: https://www.metatrader5.com/")
    print("\n  3. Edit config/metatrader_config.json:")
    print("     • Replace account number")
    print("     • Replace password")
    print("     • Replace server name (get from your broker)")
    print("\n  4. Test the connection:")
    print("     python examples/metatrader_example.py")
    print("\n⚠️  Important Notes:")
    print("  • MetaTrader 5 terminal must be running on the same machine")
    print("  • Use demo account first to test")
    print("  • Keep your credentials secure")
    print("  • MetaTrader5 package only works on Windows")


if __name__ == "__main__":
    setup_metatrader_config()
