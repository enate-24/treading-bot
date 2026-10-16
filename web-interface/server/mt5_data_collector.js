/**
 * MetaTrader 5 Data Collector
 * Interfaces directly with MT5 to get real-time trading data
 */

const fs = require('fs-extra');
const path = require('path');
const { spawn } = require('child_process');

class MT5DataCollector {
  constructor(configPath = '../../config/metatrader_config.json') {
    this.configPath = path.join(__dirname, configPath);
    this.dataFile = path.join(__dirname, './data/mt5_realtime.json');
    this.isCollecting = false;
    this.collectionInterval = null;
    this.pythonProcess = null;
    
    // Ensure data directory exists
    fs.ensureDirSync(path.dirname(this.dataFile));
  }

  async startCollection() {
    if (this.isCollecting) {
      console.log('MT5 data collection already running');
      return;
    }

    try {
      // Load MT5 configuration
      const config = await fs.readJson(this.configPath);
      
      console.log('Starting MT5 data collection...');
      this.isCollecting = true;
      
      // Start periodic data collection
      this.collectionInterval = setInterval(() => {
        this.collectMT5Data(config);
      }, 5000); // Collect every 5 seconds
      
      console.log('MT5 data collection started');
    } catch (error) {
      console.error('Failed to start MT5 data collection:', error);
      this.isCollecting = false;
    }
  }

  stopCollection() {
    if (this.collectionInterval) {
      clearInterval(this.collectionInterval);
      this.collectionInterval = null;
    }
    
    if (this.pythonProcess) {
      this.pythonProcess.kill();
      this.pythonProcess = null;
    }
    
    this.isCollecting = false;
    console.log('MT5 data collection stopped');
  }

  async collectMT5Data(config) {
    try {
      // Create a Python script to collect MT5 data
      const pythonScript = this.createMT5Script(config);
      const scriptPath = path.join(__dirname, 'temp_mt5_collector.py');
      
      // Write temporary Python script
      await fs.writeFile(scriptPath, pythonScript);
      
      // Execute Python script
      const pythonProcess = spawn('python', [scriptPath], {
        cwd: path.join(__dirname, '../..'),
        stdio: ['pipe', 'pipe', 'pipe']
      });

      let output = '';
      let errorOutput = '';

      pythonProcess.stdout.on('data', (data) => {
        output += data.toString();
      });

      pythonProcess.stderr.on('data', (data) => {
        errorOutput += data.toString();
      });

      pythonProcess.on('close', async (code) => {
        try {
          // Clean up temporary script
          await fs.remove(scriptPath);
          
          if (code === 0 && output.trim()) {
            // Parse and save the collected data
            const data = JSON.parse(output.trim());
            await this.saveCollectedData(data);
          } else if (errorOutput) {
            console.error('MT5 collection error:', errorOutput);
          }
        } catch (error) {
          console.error('Error processing MT5 data:', error);
        }
      });

    } catch (error) {
      console.error('Error in MT5 data collection:', error);
    }
  }

  createMT5Script(config) {
    return `
import sys
import json
from datetime import datetime
import MetaTrader5 as mt5

def collect_mt5_data():
    try:
        # Initialize MT5
        if not mt5.initialize():
            return {"error": "MT5 initialization failed"}
        
        # Login to account
        account = ${config.metatrader.account}
        password = "${config.metatrader.password}"
        server = "${config.metatrader.server}"
        
        if not mt5.login(account, password=password, server=server):
            return {"error": "MT5 login failed"}
        
        # Collect account information
        account_info = mt5.account_info()
        if account_info is None:
            return {"error": "Failed to get account info"}
        
        # Collect positions
        positions = mt5.positions_get()
        positions_data = []
        if positions:
            for pos in positions:
                positions_data.append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": pos.type,
                    "volume": pos.volume,
                    "price_open": pos.price_open,
                    "price_current": pos.price_current,
                    "profit": pos.profit,
                    "swap": pos.swap,
                    "comment": pos.comment,
                    "time": pos.time
                })
        
        # Collect recent orders/deals
        from datetime import datetime, timedelta
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)  # Last hour
        
        deals = mt5.history_deals_get(start_time, end_time)
        deals_data = []
        if deals:
            for deal in deals[-20:]:  # Last 20 deals
                deals_data.append({
                    "ticket": deal.ticket,
                    "order": deal.order,
                    "symbol": deal.symbol,
                    "type": deal.type,
                    "entry": deal.entry,
                    "volume": deal.volume,
                    "price": deal.price,
                    "profit": deal.profit,
                    "swap": deal.swap,
                    "commission": deal.commission,
                    "time": deal.time,
                    "comment": deal.comment
                })
        
        # Collect symbol prices
        symbols = ${JSON.stringify(config.trading.symbols)}
        prices_data = {}
        for symbol in symbols:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                prices_data[symbol] = {
                    "bid": tick.bid,
                    "ask": tick.ask,
                    "last": tick.last,
                    "volume": tick.volume,
                    "time": tick.time,
                    "spread": tick.ask - tick.bid
                }
        
        # Prepare response data
        data = {
            "timestamp": datetime.now().isoformat(),
            "account": {
                "login": account_info.login,
                "balance": account_info.balance,
                "equity": account_info.equity,
                "margin": account_info.margin,
                "free_margin": account_info.margin_free,
                "margin_level": account_info.margin_level,
                "profit": account_info.profit,
                "currency": account_info.currency,
                "leverage": account_info.leverage,
                "server": account_info.server,
                "company": account_info.company
            },
            "positions": positions_data,
            "recent_deals": deals_data,
            "prices": prices_data,
            "connection_status": "connected"
        }
        
        mt5.shutdown()
        return data
        
    except Exception as e:
        return {"error": str(e), "connection_status": "error"}

if __name__ == "__main__":
    result = collect_mt5_data()
    print(json.dumps(result, default=str))
`;
  }

  async saveCollectedData(data) {
    try {
      // Add timestamp
      data.collected_at = new Date().toISOString();
      
      // Save to file
      await fs.writeJson(this.dataFile, data, { spaces: 2 });
      
      // Also save to history for performance tracking
      const historyFile = path.join(__dirname, './data/mt5_history.jsonl');
      const historyLine = JSON.stringify(data) + '\n';
      await fs.appendFile(historyFile, historyLine);
      
    } catch (error) {
      console.error('Error saving MT5 data:', error);
    }
  }

  async getLatestData() {
    try {
      if (await fs.pathExists(this.dataFile)) {
        return await fs.readJson(this.dataFile);
      }
      return null;
    } catch (error) {
      console.error('Error reading MT5 data:', error);
      return null;
    }
  }

  async getHistoricalData(hours = 24) {
    try {
      const historyFile = path.join(__dirname, './data/mt5_history.jsonl');
      
      if (!(await fs.pathExists(historyFile))) {
        return [];
      }
      
      const content = await fs.readFile(historyFile, 'utf8');
      const lines = content.trim().split('\n').filter(line => line.trim());
      
      const cutoffTime = new Date(Date.now() - hours * 60 * 60 * 1000);
      
      return lines
        .map(line => {
          try {
            return JSON.parse(line);
          } catch {
            return null;
          }
        })
        .filter(data => data && new Date(data.collected_at) > cutoffTime)
        .slice(-1000); // Keep last 1000 records max
        
    } catch (error) {
      console.error('Error reading MT5 history:', error);
      return [];
    }
  }

  isRunning() {
    return this.isCollecting;
  }
}

module.exports = MT5DataCollector;