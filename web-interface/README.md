# HFT Trading Bot - Web Interface

A comprehensive React + Node.js monitoring interface for the High-Frequency Trading bot system.

## 🚀 Features

### Real-Time Monitoring
- **Live Dashboard** with key metrics and performance indicators
- **Real-time Charts** showing profit/loss, trade activity, and win rates
- **Signal Tracking** with live signal generation monitoring
- **Position Management** with open positions and portfolio overview

### Performance Analytics
- **Historical Performance** with hourly and daily views
- **Trade Distribution** analysis by currency pairs
- **Win/Loss Analysis** with detailed statistics
- **Risk Metrics** including drawdown, Sharpe ratio, and more

### Configuration Management
- **Strategy Configuration** for HFT, Scalping, and Swing Trading
- **Risk Management** settings with real-time validation
- **HFT Parameters** fine-tuning for optimal performance
- **MetaTrader Connection** status and settings

### System Logs
- **Real-time Log Monitoring** with filtering and search
- **Log Categories** (Info, Warning, Error, Success)
- **Export Functionality** for log analysis
- **Auto-scroll** and live updates

## 📋 Prerequisites

- Node.js 16+ and npm
- Python 3.8+ (for the trading bot)
- MetaTrader 5 terminal
- Active trading account

## 🛠️ Installation

### 1. Install Dependencies

```bash
# Navigate to web interface directory
cd web-interface

# Install all dependencies (root, server, and client)
npm run install-all
```

### 2. Alternative Manual Installation

```bash
# Install root dependencies
npm install

# Install server dependencies
cd server
npm install

# Install client dependencies
cd ../client
npm install
```

## 🚀 Running the Application

### Development Mode (Recommended)
```bash
# From web-interface directory
npm run dev
```
This starts both the server (port 5000) and client (port 3000) concurrently.

### Production Mode
```bash
# Build the client
npm run build

# Start the server
npm start
```

### Individual Components
```bash
# Start only the server
npm run server

# Start only the client (in another terminal)
npm run client
```

## 🌐 Access Points

- **Web Dashboard**: http://localhost:3000
- **API Server**: http://localhost:5000
- **API Documentation**: http://localhost:5000/api

## 📊 Dashboard Overview

### Main Dashboard
- **Bot Status**: Current running state and key metrics
- **Performance Chart**: Real-time profit/loss visualization
- **Recent Signals**: Latest trading signals generated
- **System Messages**: Important notifications and alerts

### Performance Page
- **Time-based Analysis**: Hourly and daily performance views
- **Trade Distribution**: Breakdown by currency pairs
- **Risk Metrics**: Comprehensive risk analysis
- **Win/Loss Statistics**: Detailed trading performance

### Configuration Page
- **Trading Settings**: Symbol selection, timeframes, strategy
- **Risk Management**: Drawdown limits, position sizing
- **HFT Parameters**: Fine-tuning for high-frequency trading
- **Connection Settings**: MetaTrader configuration

### Logs Page
- **Real-time Monitoring**: Live log streaming
- **Filtering & Search**: Advanced log analysis tools
- **Export Options**: Download logs for external analysis
- **Statistics**: Log type distribution and counts

## 🔧 Configuration

### Server Configuration
The server automatically monitors:
- `../../metatrader_bot.log` - Trading bot log file
- `../../config/metatrader_config.json` - Main configuration
- `../../config/metatrader_config_hft.json` - HFT configuration

### Environment Variables
```bash
PORT=5000                    # Server port (default: 5000)
CLIENT_URL=http://localhost:3000  # Client URL for CORS
```

### API Endpoints

#### Bot Control
- `POST /api/bot/start` - Start the trading bot
- `POST /api/bot/stop` - Stop the trading bot
- `GET /api/bot/status` - Get current bot status

#### Configuration
- `GET /api/config` - Get current configuration
- `POST /api/config` - Update configuration
- `GET /api/config/hft` - Get HFT-specific configuration

#### Data
- `GET /api/performance` - Get performance data
- `GET /api/trades` - Get trade history
- `GET /api/logs` - Get system logs

#### WebSocket Events
- `botStatus` - Real-time bot status updates
- `realtimeData` - Live trading data
- `performanceUpdate` - Performance metrics updates
- `logUpdate` - New log entries

## 🔒 Security Features

- **CORS Protection** with configurable origins
- **Input Validation** for all configuration changes
- **Error Handling** with graceful degradation
- **Rate Limiting** for API endpoints (production)

## 📱 Mobile Responsive

The interface is fully responsive and works on:
- Desktop computers (1200px+)
- Tablets (768px - 1199px)
- Mobile phones (< 768px)

## 🎨 Customization

### Themes
The interface uses a dark theme optimized for trading:
- **Primary Color**: #00ff88 (Green)
- **Danger Color**: #ff4444 (Red)
- **Warning Color**: #ffaa00 (Orange)
- **Info Color**: #4488ff (Blue)

### Adding Custom Metrics
1. Update server data collection in `server/index.js`
2. Add new chart components in `client/src/components/`
3. Update the dashboard layout as needed

### Custom Strategies
To add support for new trading strategies:
1. Update configuration schema
2. Add strategy-specific parameters
3. Update the configuration UI

## 🐛 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Kill process on port 5000
   npx kill-port 5000
   
   # Or use different port
   PORT=5001 npm start
   ```

2. **WebSocket Connection Failed**
   - Check if server is running on port 5000
   - Verify firewall settings
   - Check browser console for errors

3. **Log File Not Found**
   - Ensure trading bot is running
   - Check log file path in server configuration
   - Verify file permissions

4. **Configuration Not Loading**
   - Check config file paths
   - Verify JSON syntax
   - Check file permissions

### Debug Mode
```bash
# Enable debug logging
DEBUG=* npm run server
```

## 📈 Performance Optimization

### Server Optimization
- Log file monitoring with efficient file watching
- Cached configuration data
- Optimized WebSocket updates

### Client Optimization
- Lazy loading of chart components
- Efficient re-rendering with React hooks
- Optimized bundle size with code splitting

## 🔄 Updates and Maintenance

### Updating Dependencies
```bash
# Check for outdated packages
npm outdated

# Update all dependencies
npm update

# Update client dependencies
cd client && npm update

# Update server dependencies
cd server && npm update
```

### Backup Configuration
```bash
# Backup current configuration
cp config/metatrader_config.json config/backup_$(date +%Y%m%d).json
```

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review server and client logs
3. Verify trading bot is running correctly
4. Check MetaTrader 5 connection

## 🚀 Production Deployment

### Using PM2 (Recommended)
```bash
# Install PM2
npm install -g pm2

# Start with PM2
pm2 start server/index.js --name "hft-monitor"

# Save PM2 configuration
pm2 save
pm2 startup
```

### Using Docker
```bash
# Build Docker image
docker build -t hft-monitor .

# Run container
docker run -p 5000:5000 -v $(pwd)/../../config:/app/config hft-monitor
```

### Environment Setup
```bash
# Production environment variables
NODE_ENV=production
PORT=5000
LOG_LEVEL=info
```

The web interface provides a comprehensive monitoring and control system for your HFT trading bot, enabling real-time oversight and configuration management through an intuitive web dashboard.