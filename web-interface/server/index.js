const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const fs = require('fs-extra');
const path = require('path');
const chokidar = require('chokidar');
const cron = require('node-cron');
const moment = require('moment');
const MT5DataCollector = require('./mt5_data_collector');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: "http://localhost:3000",
    methods: ["GET", "POST"]
  }
});

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, '../client/build')));

// Configuration
const CONFIG = {
  logFile: path.join(__dirname, '../../metatrader_bot.log'),
  configFile: path.join(__dirname, '../../config/metatrader_config.json'),
  hftConfigFile: path.join(__dirname, '../../config/metatrader_config_hft.json'),
  performanceFile: path.join(__dirname, './data/performance.json'),
  tradesFile: path.join(__dirname, './data/trades.json'),
  botStatusFile: path.join(__dirname, './data/bot_status.json'),
  metatraderDataFile: path.join(__dirname, './data/mt_data.json')
};

// Ensure data directory exists
fs.ensureDirSync(path.join(__dirname, './data'));

// Initialize MT5 data collector
const mt5Collector = new MT5DataCollector();

// Global state
let botStatus = {
  isRunning: false,
  lastUpdate: null,
  totalTrades: 0,
  openPositions: 0,
  balance: 10.0,
  equity: 10.0,
  profit: 0,
  winRate: 0,
  strategy: 'hft',
  signals: [],
  errors: [],
  account: '298585393',
  server: 'Exness-MT5Trial9',
  leverage: '1:2000',
  freeMargin: 9.0,
  margin: 0,
  currency: 'USD'
};

let realtimeData = {
  prices: {},
  signals: [],
  trades: [],
  performance: {
    hourly: [],
    daily: []
  },
  positions: [],
  accountInfo: {}
};

// Socket.io connection handling
io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);
  
  // Send initial data
  socket.emit('botStatus', botStatus);
  socket.emit('realtimeData', realtimeData);
  
  // Global bot process reference
  let botProcess = null;
  
  // Handle bot control commands
  socket.on('startBot', async (config) => {
    try {
      const { spawn } = require('child_process');
      
      // Stop existing bot if running
      if (botProcess) {
        botProcess.kill();
        botProcess = null;
      }
      
      // Determine which bot to start
      let scriptName = 'run_session_based_bot.py'; // Default to session-based
      let configPath = path.join(__dirname, '../../config/metatrader_config_session_based.json');
      
      if (config.useHFT) {
        scriptName = 'run_metatrader_bot.py';
        configPath = CONFIG.hftConfigFile;
      } else if (config.useUltraAggressive) {
        scriptName = 'run_ultra_aggressive_bot.py';
        configPath = path.join(__dirname, '../../config/metatrader_config_ultra_aggressive.json');
      }
      
      console.log(`Starting bot: ${scriptName} with config: ${configPath}`);
      
      botProcess = spawn('python', [scriptName, configPath, '--auto'], {
        cwd: path.join(__dirname, '../..'),
        detached: false,
        stdio: ['ignore', 'pipe', 'pipe']
      });
      
      // Capture stdout
      botProcess.stdout.on('data', (data) => {
        const output = data.toString();
        console.log('Bot stdout:', output);
        socket.emit('message', { type: 'info', text: output });
      });
      
      // Capture stderr
      botProcess.stderr.on('data', (data) => {
        const error = data.toString();
        console.error('Bot stderr:', error);
        socket.emit('message', { type: 'error', text: error });
      });
      
      // Handle process exit
      botProcess.on('exit', (code, signal) => {
        console.log(`Bot process exited with code ${code} and signal ${signal}`);
        botStatus.isRunning = false;
        botStatus.lastUpdate = new Date();
        io.emit('botStatus', botStatus);
        
        if (code !== 0 && code !== null) {
          socket.emit('message', { 
            type: 'error', 
            text: `Bot stopped unexpectedly with exit code ${code}. Check logs for details.` 
          });
        } else {
          socket.emit('message', { type: 'info', text: 'Bot stopped' });
        }
        
        botProcess = null;
      });
      
      // Handle process errors
      botProcess.on('error', (error) => {
        console.error('Bot process error:', error);
        botStatus.isRunning = false;
        botStatus.lastUpdate = new Date();
        io.emit('botStatus', botStatus);
        socket.emit('message', { 
          type: 'error', 
          text: `Failed to start bot: ${error.message}. Make sure Python is installed and in PATH.` 
        });
        botProcess = null;
      });
      
      // Wait a moment to see if process starts successfully
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      if (botProcess && !botProcess.killed) {
        botStatus.isRunning = true;
        botStatus.lastUpdate = new Date();
        
        // Start MT5 data collection
        await mt5Collector.startCollection();
        
        io.emit('botStatus', botStatus);
        socket.emit('message', { type: 'success', text: 'Bot started successfully' });
      } else {
        throw new Error('Bot process failed to start');
      }
      
    } catch (error) {
      console.error('Error starting bot:', error);
      botStatus.isRunning = false;
      io.emit('botStatus', botStatus);
      socket.emit('message', { type: 'error', text: `Failed to start bot: ${error.message}` });
    }
  });
  
  socket.on('stopBot', () => {
    try {
      if (botProcess) {
        console.log('Stopping bot process...');
        botProcess.kill('SIGTERM');
        
        // Force kill after 5 seconds if still running
        setTimeout(() => {
          if (botProcess && !botProcess.killed) {
            console.log('Force killing bot process...');
            botProcess.kill('SIGKILL');
          }
        }, 5000);
      }
      
      botStatus.isRunning = false;
      botStatus.lastUpdate = new Date();
      
      // Stop MT5 data collection
      mt5Collector.stopCollection();
      
      io.emit('botStatus', botStatus);
      socket.emit('message', { type: 'info', text: 'Bot stop signal sent' });
      
    } catch (error) {
      console.error('Error stopping bot:', error);
      socket.emit('message', { type: 'error', text: `Error stopping bot: ${error.message}` });
    }
  });
  
  socket.on('getConfig', async () => {
    try {
      const config = await fs.readJson(CONFIG.configFile);
      const hftConfig = await fs.readJson(CONFIG.hftConfigFile);
      
      socket.emit('configData', {
        standard: config,
        hft: hftConfig
      });
    } catch (error) {
      socket.emit('message', { type: 'error', text: 'Failed to load configuration' });
    }
  });
  
  socket.on('updateConfig', async (configData) => {
    try {
      const configPath = configData.type === 'hft' ? CONFIG.hftConfigFile : CONFIG.configFile;
      await fs.writeJson(configPath, configData.config, { spaces: 2 });
      
      socket.emit('message', { type: 'success', text: 'Configuration updated successfully' });
    } catch (error) {
      socket.emit('message', { type: 'error', text: 'Failed to update configuration' });
    }
  });
  
  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
  });
});

// Log file monitoring
function startLogMonitoring() {
  if (!fs.existsSync(CONFIG.logFile)) {
    console.log('Log file not found, creating watcher for when it appears...');
  }
  
  const watcher = chokidar.watch(CONFIG.logFile, { ignoreInitial: false });
  
  watcher.on('change', () => {
    parseLogFile();
  });
  
  watcher.on('add', () => {
    console.log('Log file detected, starting monitoring...');
    parseLogFile();
  });
}

// Real log analysis function
async function analyzeRealTradingLogs(lines) {
  const signals = [];
  const orders = [];
  const closedPositions = [];
  const botStarts = [];
  const connections = [];
  const errors = [];
  let latestBalance = null;
  let latestEquity = null;
  
  lines.forEach(line => {
    if (!line.trim()) return;
    
    // Support multiple timestamp formats
    // ISO format: 2024-02-23T17:28:50.760Z
    // Python format: 2026-02-23 21:10:17,772
    const isoMatch = line.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)/);
    const pythonMatch = line.match(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d{3})/);
    
    let timestamp;
    let message;
    
    if (isoMatch) {
      timestamp = new Date(isoMatch[1]);
      message = line.substring(isoMatch[0].length);
    } else if (pythonMatch) {
      // Convert Python format to ISO
      timestamp = new Date(`${pythonMatch[1]}.${pythonMatch[2]}`);
      message = line.substring(pythonMatch[0].length);
    } else {
      return; // Skip lines without valid timestamp
    }
    
    // Parse balance from logs
    const balanceMatch = message.match(/Balance:\s*\$?([\d.]+)\s*USD/i);
    if (balanceMatch) {
      latestBalance = parseFloat(balanceMatch[1]);
    }
    
    // Parse equity from logs
    const equityMatch = message.match(/Equity:\s*\$?([\d.]+)/i);
    if (equityMatch) {
      latestEquity = parseFloat(equityMatch[1]);
    }
    
    // Parse signals - look for various signal patterns
    const signalMatch = message.match(/\[SIGNAL\].*?(BUY|SELL)\s+(\w+m?)|Signal generated:\s*(BUY|SELL)\s+(\w+)/i);
    if (signalMatch) {
      signals.push({
        timestamp: timestamp,
        direction: signalMatch[1] || signalMatch[3],
        symbol: signalMatch[2] || signalMatch[4],
        message: message
      });
    }
    
    // Parse orders - look for order placement
    const orderMatch = message.match(/\[ORDER\].*?(\d+)\s+lots|Order placed successfully:\s*(\d+)|ticket.*?(\d{6,})/i);
    if (orderMatch) {
      orders.push({
        timestamp: timestamp,
        orderId: orderMatch[1] || orderMatch[2] || orderMatch[3],
        message: message
      });
    }
    
    // Also count successful trades
    if (message.match(/\[SUCCESS\].*?Trade #(\d+)/i)) {
      const tradeMatch = message.match(/Trade #(\d+)/);
      if (tradeMatch) {
        orders.push({
          timestamp: timestamp,
          orderId: tradeMatch[1],
          message: message
        });
      }
    }
    
    // Parse closed positions
    const positionMatch = message.match(/Position closed.*?profit.*?([-+]?[\d.]+)|📍 Position closed:\s+(\w+)/i);
    if (positionMatch) {
      closedPositions.push({
        timestamp: timestamp,
        profit: positionMatch[1] ? parseFloat(positionMatch[1]) : 0,
        symbol: positionMatch[2] || 'UNKNOWN',
        message: message
      });
    }
    
    // Parse bot starts
    if (message.includes('Bot started') || message.includes('START') || message.includes('Initializing')) {
      botStarts.push({
        timestamp: timestamp,
        message: message
      });
    }
    
    // Parse connections
    if (message.includes('Connected to MetaTrader') || message.includes('MT5 initialized')) {
      connections.push({
        timestamp: timestamp,
        message: message
      });
    }
    
    // Parse errors
    if (message.includes('ERROR') || message.includes('Error')) {
      errors.push({
        timestamp: timestamp,
        message: message
      });
    }
  });
  
  // Calculate metrics
  const totalProfit = closedPositions.reduce((sum, pos) => sum + pos.profit, 0);
  const winningTrades = closedPositions.filter(pos => pos.profit > 0);
  const winRate = closedPositions.length > 0 ? (winningTrades.length / closedPositions.length) * 100 : 0;
  const openPositions = Math.max(0, orders.length - closedPositions.length);
  
  // Format signals for dashboard
  const signalsData = signals.map(signal => ({
    direction: signal.direction,
    symbol: signal.symbol,
    timestamp: signal.timestamp.toISOString(),
    type: 'signal'
  }));
  
  // Format trades for dashboard
  const tradesData = closedPositions.map(pos => ({
    timestamp: pos.timestamp.toISOString(),
    profit: pos.profit,
    type: 'close',
    symbol: 'UNKNOWN'
  }));
  
  return {
    signals: signals.length,
    orders: orders.length,
    closed_positions: closedPositions.length,
    open_positions: openPositions,
    total_profit: totalProfit,
    win_rate: winRate,
    avg_profit: closedPositions.length > 0 ? totalProfit / closedPositions.length : 0,
    signals_data: signalsData,
    trades_data: tradesData,
    bot_active: botStarts.length > 0,
    connections: connections.length,
    errors: errors.length,
    balance: latestBalance,
    equity: latestEquity
  };
}

// Parse log file for real-time data
async function parseLogFile() {
  try {
    if (!fs.existsSync(CONFIG.logFile)) return;
    
    const logContent = await fs.readFile(CONFIG.logFile, 'utf8');
    const lines = logContent.split('\n').slice(-200);
    
    // Use the real log analysis
    const analysisResults = await analyzeRealTradingLogs(lines);
    
    // Update bot status with real data
    botStatus.totalTrades = analysisResults.closed_positions;
    botStatus.openPositions = analysisResults.open_positions;
    botStatus.profit = analysisResults.total_profit;
    botStatus.winRate = analysisResults.win_rate / 100;
    botStatus.signals = analysisResults.signals_data || [];
    botStatus.lastUpdate = new Date();
    
    // Update balance and equity from logs if available
    if (analysisResults.balance !== null) {
      botStatus.balance = analysisResults.balance;
    }
    if (analysisResults.equity !== null) {
      botStatus.equity = analysisResults.equity;
    }
    
    const newSignals = analysisResults.signals_data || [];
    const newTrades = analysisResults.trades_data || [];
    
    // Update realtime data
    realtimeData.signals = [...newSignals];
    realtimeData.trades = [...newTrades];
    
    // Update performance data
    if (analysisResults.total_profit > 0) {
      const now = new Date();
      const hourlyData = {
        timestamp: now.toISOString(),
        profit: analysisResults.total_profit,
        trades: analysisResults.closed_positions,
        winRate: analysisResults.win_rate / 100
      };
      
      realtimeData.performance.hourly.push(hourlyData);
      realtimeData.performance.hourly = realtimeData.performance.hourly.slice(-24);
    }
    
    // Update account info - only if not already set from logs
    if (analysisResults.equity === null && analysisResults.balance !== null) {
      botStatus.equity = botStatus.balance + analysisResults.total_profit;
    }
    
    // Check for recent activity
    const now = new Date();
    const recentLogs = lines.filter(line => {
      // Support both ISO and Python timestamp formats
      const isoMatch = line.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)/);
      const pythonMatch = line.match(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d{3})/);
      
      if (isoMatch) {
        const logTime = new Date(isoMatch[1]);
        const timeDiff = now - logTime;
        return timeDiff < 300000; // Last 5 minutes
      } else if (pythonMatch) {
        const logTime = new Date(`${pythonMatch[1]}.${pythonMatch[2]}`);
        const timeDiff = now - logTime;
        return timeDiff < 300000; // Last 5 minutes
      }
      return false;
    });
    
    // Update connection status
    if (recentLogs.length > 0) {
      botStatus.isRunning = true;
      botStatus.lastUpdate = new Date();
    } else {
      botStatus.isRunning = false;
    }
    
    // Save state
    await saveCurrentState();
    
    // Emit updates
    io.emit('botStatus', botStatus);
    io.emit('realtimeData', realtimeData);
    
    console.log(`📊 Real data update: ${analysisResults.signals} signals, ${analysisResults.orders} orders, ${analysisResults.closed_positions} trades, $${analysisResults.total_profit.toFixed(2)} profit, ${analysisResults.win_rate.toFixed(1)}% win rate`);
    
  } catch (error) {
    console.error('Error parsing log file:', error);
  }
}

function extractTimestamp(logLine) {
  // Handle multiple timestamp formats
  const isoMatch = logLine.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)/);
  if (isoMatch) {
    return new Date(isoMatch[1]);
  }
  
  const standardMatch = logLine.match(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d{3})/);
  if (standardMatch) {
    return new Date(`${standardMatch[1]}.${standardMatch[2]}`);
  }
  
  const simpleMatch = logLine.match(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/);
  if (simpleMatch) {
    return new Date(simpleMatch[1]);
  }
  
  return new Date();
}

// Save current state
async function saveCurrentState() {
  try {
    const state = {
      botStatus,
      realtimeData,
      timestamp: new Date().toISOString()
    };
    
    await fs.writeJson(CONFIG.botStatusFile, state, { spaces: 2 });
  } catch (error) {
    console.error('Error saving state:', error);
  }
}

// Load previous state
async function loadPreviousState() {
  try {
    if (await fs.pathExists(CONFIG.botStatusFile)) {
      const state = await fs.readJson(CONFIG.botStatusFile);
      
      if (state.botStatus) {
        botStatus = { ...botStatus, ...state.botStatus };
      }
      
      if (state.realtimeData) {
        realtimeData = { ...realtimeData, ...state.realtimeData };
      }
      
      console.log('Previous state loaded successfully');
    }
  } catch (error) {
    console.error('Error loading previous state:', error);
  }
}

// Generate performance data
function generateRealPerformanceData() {
  try {
    const now = new Date();
    
    // Generate hourly data points
    for (let i = 23; i >= 0; i--) {
      const timestamp = new Date(now.getTime() - (i * 60 * 60 * 1000));
      
      const existingData = realtimeData.performance.hourly.find(
        item => new Date(item.timestamp).getHours() === timestamp.getHours()
      );
      
      if (!existingData) {
        realtimeData.performance.hourly.push({
          timestamp: timestamp.toISOString(),
          profit: botStatus.profit || 0,
          trades: botStatus.totalTrades || 0,
          winRate: botStatus.winRate || 0
        });
      }
    }
    
    // Keep only last 24 hours
    realtimeData.performance.hourly = realtimeData.performance.hourly.slice(-24);
    
  } catch (error) {
    console.error('Error generating performance data:', error);
  }
}

// Update with MT5 data
async function updateWithMT5Data() {
  try {
    const mt5Data = await mt5Collector.getLatestData();
    
    if (mt5Data && mt5Data.account_info) {
      // Update bot status with real MT5 data
      botStatus.balance = mt5Data.account_info.balance || botStatus.balance;
      botStatus.equity = mt5Data.account_info.equity || botStatus.equity;
      botStatus.freeMargin = mt5Data.account_info.margin_free || botStatus.freeMargin;
      botStatus.margin = mt5Data.account_info.margin || botStatus.margin;
      
      // Update positions
      if (mt5Data.positions) {
        botStatus.openPositions = mt5Data.positions.length;
        realtimeData.positions = mt5Data.positions;
      }
      
      // Update prices
      if (mt5Data.prices) {
        realtimeData.prices = mt5Data.prices;
      }
      
      // Update connection status
      botStatus.isRunning = mt5Data.connection_status === 'connected';
      botStatus.lastUpdate = new Date();
      
      // Emit updates
      io.emit('botStatus', botStatus);
      io.emit('realtimeData', realtimeData);
    }
    
  } catch (error) {
    console.error('Error updating with MT5 data:', error);
  }
}

// API Routes
app.get('/api/status', (req, res) => {
  res.json(botStatus);
});

app.get('/api/performance', (req, res) => {
  res.json(realtimeData.performance);
});

app.get('/api/trades', (req, res) => {
  res.json(realtimeData.trades);
});

app.get('/api/symbol-stats', async (req, res) => {
  try {
    const { getSymbolStats } = require('./get_symbol_stats');
    const stats = await getSymbolStats();
    res.json(stats || { symbols: [] });
  } catch (error) {
    console.error('Error getting symbol stats:', error);
    res.json({ symbols: [] });
  }
});

app.get('/api/performance-data', async (req, res) => {
  try {
    const { spawn } = require('child_process');
    const path = require('path');
    
    const pythonScript = path.join(__dirname, '../../get_performance_data.py');
    const python = spawn('python', [pythonScript]);
    
    let dataString = '';
    let errorString = '';
    
    python.stdout.on('data', (data) => {
      dataString += data.toString();
    });
    
    python.stderr.on('data', (data) => {
      errorString += data.toString();
    });
    
    python.on('close', (code) => {
      if (code !== 0) {
        console.error('Error getting performance data:', errorString);
        res.json({ error: 'Failed to get performance data' });
        return;
      }
      
      try {
        const perfData = JSON.parse(dataString);
        res.json(perfData);
      } catch (error) {
        console.error('Error parsing performance data:', error);
        res.json({ error: 'Failed to parse performance data' });
      }
    });
  } catch (error) {
    console.error('Error getting performance data:', error);
    res.json({ error: 'Failed to get performance data' });
  }
});

app.get('/api/positions', (req, res) => {
  res.json(realtimeData.positions || []);
});

app.get('/api/prices', (req, res) => {
  res.json(realtimeData.prices || {});
});

app.get('/api/logs', async (req, res) => {
  try {
    // Read real log file
    if (await fs.pathExists(CONFIG.logFile)) {
      const logContent = await fs.readFile(CONFIG.logFile, 'utf8');
      const lines = logContent.split('\n').filter(line => line.trim()).slice(-100); // Last 100 lines
      
      const logs = lines.map((line, index) => {
        // Parse log format: YYYY-MM-DDTHH:MM:SS.mmmZ [LEVEL] SOURCE: message
        const match = line.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z|\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})\s+\[?(\w+)\]?\s+-?\s*(\w+)?\s*-?\s*(.+)$/);
        
        if (match) {
          return {
            id: index,
            timestamp: match[1],
            type: match[2] || 'INFO',
            source: match[3] || 'SYSTEM',
            message: match[4] || line
          };
        }
        
        return {
          id: index,
          timestamp: new Date().toISOString(),
          type: 'INFO',
          source: 'SYSTEM',
          message: line
        };
      });
      
      res.json(logs.reverse()); // Most recent first
    } else {
      res.json([]);
    }
  } catch (error) {
    console.error('Error reading logs:', error);
    res.json([]);
  }
});

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    version: process.version,
    bot_running: botStatus.isRunning,
    last_update: botStatus.lastUpdate
  });
});

// Serve React app
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../client/build/index.html'));
});

// Scheduled tasks
cron.schedule('*/5 * * * * *', () => {
  parseLogFile();
});

cron.schedule('*/10 * * * * *', () => {
  generateRealPerformanceData();
  io.emit('performanceUpdate', realtimeData.performance);
});

cron.schedule('0 */5 * * * *', () => {
  saveCurrentState();
});

// Initialize
const PORT = process.env.PORT || 5000;

server.listen(PORT, () => {
  console.log(`HFT Monitor Server running on port ${PORT}`);
  console.log(`Dashboard: http://localhost:${PORT}`);
  
  // Load previous state
  loadPreviousState();
  
  // Start monitoring
  startLogMonitoring();
  generateRealPerformanceData();
  
  // Start MT5 data collection if bot should be running
  if (botStatus.isRunning) {
    mt5Collector.startCollection();
  }
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down server...');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});