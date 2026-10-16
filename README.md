# Trading Bot System

A comprehensive Python-based algorithmic trading platform designed for **fully automated trading** across multiple exchanges with configurable strategies, robust risk management, and real-time monitoring.

## 🤖 Fully Automated Trading

**Yes, this bot trades automatically!** Once started, it:
- ✅ Monitors markets 24/7
- ✅ Generates trading signals automatically
- ✅ Executes trades without manual intervention
- ✅ Manages risk and positions
- ✅ Tracks performance in real-time

## Quick Start

### Cryptocurrency Trading (Binance, Coinbase, etc.)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup configuration
python setup_production_bot.py

# 3. Add your API keys to config/production_config.json

# 4. Start the bot (it will trade automatically)
python run_trading_bot.py
```

### Forex/CFD Trading (MetaTrader 4/5)

```bash
# 1. Install MetaTrader package
pip install MetaTrader5

# 2. Start MetaTrader 5 terminal

# 3. Setup configuration
python setup_metatrader.py

# 4. Add your credentials to config/metatrader_config.json

# 5. Start the bot (it will trade automatically)
python run_metatrader_bot.py
```

**That's it!** The bot will now trade automatically based on your configuration.

## Features

- **🤖 Fully Automated**: Trades 24/7 without manual intervention
- **Multiple Trading Strategies**: Scalping and swing trading strategies with configurable parameters
- **Risk Management**: Comprehensive risk controls with stop-loss, take-profit, and portfolio-level limits
- **Real-time Data Processing**: Low-latency market data processing with technical indicators
- **Performance Monitoring**: Detailed performance analytics with Sharpe ratio, drawdown tracking
- **Exchange Integration**: Support for multiple cryptocurrency exchanges via APIs
- **MetaTrader Support**: Direct integration with MetaTrader 4/5 for forex and CFD trading
- **Compliance**: Audit trails and regulatory compliance features
- **Backtesting**: Historical data backtesting and paper trading capabilities

## How It Works

The bot operates in a continuous automated loop:

1. **Market Monitoring**: Subscribes to real-time price feeds for configured symbols
2. **Technical Analysis**: Calculates indicators (RSI, Moving Averages, Volume, MACD)
3. **Signal Generation**: Strategy analyzes data and generates BUY/SELL signals
4. **Risk Validation**: Every signal validated against risk parameters before execution
5. **Order Execution**: Approved trades automatically placed on exchange/broker
6. **Position Management**: Monitors positions and enforces stop-loss/take-profit
7. **Performance Tracking**: Records all activity and calculates metrics

### Trading Flow

```
Market Data → Indicators → Strategy Analysis → Risk Check → Auto Execute → Monitor Positions
```

## Documentation

- **[QUICK_START.md](QUICK_START.md)**: Get started in 5 minutes
- **[BOT_DOCUMENTATION.md](BOT_DOCUMENTATION.md)**: Complete system documentation (86KB)
- **[METATRADER_GUIDE.md](METATRADER_GUIDE.md)**: MetaTrader integration guide

## Project Structure

```
trading_bot/
├── __init__.py
├── models/                 # Core data models
│   ├── __init__.py
│   ├── core.py            # Price, MarketData, TradingSignal, etc.
│   └── enums.py           # Enumerations for trading
├── interfaces/            # Abstract base classes
│   ├── __init__.py
│   ├── data_handler.py
│   ├── signal_generator.py
│   ├── portfolio_manager.py
│   ├── risk_manager.py
│   ├── execution_engine.py
│   ├── performance_monitor.py
│   ├── configuration_manager.py
│   └── compliance_system.py
└── components/            # Implementation classes (to be added)

tests/
├── __init__.py
├── conftest.py           # Pytest configuration and fixtures
├── test_models.py        # Unit tests for data models
└── test_interfaces.py    # Unit tests for interfaces
```

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install the package in development mode:
   ```bash
   pip install -e .
   ```

## Configuration

### MetaTrader 4/5 Integration (Forex/CFD Trading)

To connect with your broker via MetaTrader:

1. Install MetaTrader 5 terminal from your broker or [metatrader5.com](https://www.metatrader5.com/)

2. Install the MetaTrader5 Python package:
   ```bash
   pip install MetaTrader5
   ```
   Note: MetaTrader5 package only works on Windows

3. Run the setup script:
   ```bash
   python setup_metatrader.py
   ```

4. Edit `config/metatrader_config.json` with your credentials:
   ```json
   {
     "metatrader": {
       "account": 12345678,
       "password": "your_password",
       "server": "YourBroker-Demo",
       "version": 5,
       "enabled": true
     }
   }
   ```

5. Test the connection:
   ```bash
   python examples/metatrader_example.py
   ```

Features:
- Real-time market data from MetaTrader
- Place market and pending orders
- Manage open positions
- Get account information and balance
- Support for forex, indices, commodities, and CFDs
- Compatible with most MT4/MT5 brokers

### Cryptocurrency Exchange Integration

For cryptocurrency trading (Binance, Coinbase, etc.):

### Development/Testing Mode

For testing with sandbox/testnet exchanges:
```python
from trading_bot.configuration_manager import ConfigurationManager
from trading_bot.models.config import Environment

config_manager = ConfigurationManager(
    config_dir="config",
    environment=Environment.DEVELOPMENT
)
```

### Production Mode (Real Trading)

⚠️ **WARNING**: Production mode uses real funds. Test thoroughly before deploying.

1. Run the setup script:
   ```bash
   python setup_production_bot.py
   ```

2. Edit `config/production_config.json` and add your real API credentials

3. Load the production configuration:
   ```python
   config_manager = ConfigurationManager(
       config_dir="config",
       environment=Environment.PRODUCTION
   )
   config = config_manager.load_configuration("production_config.json")
   ```

Key differences in production mode:
- `sandbox: False` - Uses real exchange APIs
- Conservative risk defaults (1% per trade, 10% max drawdown)
- API credentials are encrypted at rest
- All configuration changes are versioned and auditable

## Testing

Run the test suite:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=trading_bot
```

Run property-based tests only:
```bash
pytest -m property
```

## Requirements

- Python 3.9+
- pandas >= 2.0.0
- numpy >= 1.24.0
- pytest >= 7.0.0 (for testing)
- hypothesis >= 6.0.0 (for property-based testing)

## License

MIT License - see LICENSE file for details.
