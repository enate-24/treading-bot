/**
 * Get symbol statistics from MetaTrader 5
 */
const { spawn } = require('child_process');
const path = require('path');

async function getSymbolStats() {
  return new Promise((resolve, reject) => {
    const pythonScript = path.join(__dirname, '../../get_symbol_stats.py');
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
        console.error('Error getting symbol stats:', errorString);
        resolve(null);
        return;
      }
      
      try {
        const stats = JSON.parse(dataString);
        resolve(stats);
      } catch (error) {
        console.error('Error parsing symbol stats:', error);
        resolve(null);
      }
    });
  });
}

module.exports = { getSymbolStats };
