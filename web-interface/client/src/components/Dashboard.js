import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Square, 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Activity,
  Target,
  AlertTriangle,
  Zap,
  BarChart3,
  PieChart
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './Dashboard.css';

const Dashboard = ({ botStatus, realtimeData, onStartBot, onStopBot, messages }) => {
  const [startConfig, setStartConfig] = useState({ useHFT: true });
  const [symbolStats, setSymbolStats] = useState([]);

  // Fetch symbol statistics
  useEffect(() => {
    const fetchSymbolStats = async () => {
      try {
        const response = await fetch('/api/symbol-stats');
        const data = await response.json();
        setSymbolStats(data.symbols || []);
      } catch (error) {
        console.error('Error fetching symbol stats:', error);
      }
    };

    fetchSymbolStats();
    // Refresh every 30 seconds
    const interval = setInterval(fetchSymbolStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: botStatus.currency || 'USD',
      minimumFractionDigits: 2
    }).format(value || 0);
  };

  const formatPercentage = (value) => {
    return `${(value * 100 || 0).toFixed(1)}%`;
  };

  const getRecentSignals = () => {
    return (botStatus.signals || []).slice(-5).reverse();
  };

  const getPerformanceData = () => {
    const data = realtimeData.performance?.hourly?.slice(-12) || [];
    // Only show data if we have real trades
    return data.filter(item => item.trades > 0 || item.profit !== 0);
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>HFT Trading Dashboard</h1>
        <div className="header-actions">
          <div className="config-toggle">
            <label>
              <input
                type="checkbox"
                checked={startConfig.useHFT}
                onChange={(e) => setStartConfig({ useHFT: e.target.checked })}
              />
              Use HFT Configuration
            </label>
          </div>
          {botStatus.isRunning ? (
            <button className="btn btn-danger" onClick={onStopBot}>
              <Square size={16} />
              Stop Bot
            </button>
          ) : (
            <button className="btn btn-primary" onClick={() => onStartBot(startConfig)}>
              <Play size={16} />
              Start Bot
            </button>
          )}
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-4">
        <div className="card metric-card">
          <div className="metric-header">
            <DollarSign className="metric-icon text-green" />
            <span className="metric-title">Balance</span>
          </div>
          <div className="metric-value metric-positive">
            {formatCurrency(botStatus.balance)}
          </div>
          <div className="metric-change">
            <TrendingUp size={14} />
            {botStatus.profit >= 0 ? '+' : ''}{formatCurrency(botStatus.profit)} P&L
          </div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <Target className="metric-icon text-blue" />
            <span className="metric-title">Open Positions</span>
          </div>
          <div className="metric-value metric-neutral">
            {botStatus.openPositions || 0}
          </div>
          <div className="metric-change">
            {botStatus.leverage ? `Leverage: ${botStatus.leverage}` : 'Max: 8 positions'}
          </div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <BarChart3 className="metric-icon text-yellow" />
            <span className="metric-title">Total Trades</span>
          </div>
          <div className="metric-value metric-neutral">
            {botStatus.totalTrades || 0}
          </div>
          <div className="metric-change">
            <Activity size={14} />
            {botStatus.isRunning ? `${botStatus.strategy?.toUpperCase()} Active` : 'Inactive'}
          </div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <TrendingUp className="metric-icon text-green" />
            <span className="metric-title">Win Rate</span>
          </div>
          <div className="metric-value metric-positive">
            {formatPercentage(botStatus.winRate)}
          </div>
          <div className="metric-change">
            Target: {botStatus.totalTrades > 0 ? '65%+' : 'No trades yet'}
          </div>
        </div>
      </div>

      <div className="grid grid-2">
        {/* Performance Chart */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Performance (Last 12 Hours)</h3>
            <div className="chart-legend">
              <span className="legend-item">
                <div className="legend-color" style={{ backgroundColor: '#00ff88' }}></div>
                Profit/Loss ({botStatus.currency || 'USD'})
              </span>
            </div>
          </div>
          <div className="chart-container">
            {getPerformanceData().length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={getPerformanceData()}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis 
                    dataKey="timestamp" 
                    tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    stroke="#888888"
                  />
                  <YAxis stroke="#888888" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(0,0,0,0.8)', 
                      border: '1px solid rgba(255,255,255,0.2)',
                      borderRadius: '8px'
                    }}
                    labelFormatter={(value) => new Date(value).toLocaleString()}
                    formatter={(value) => [formatCurrency(value), 'Profit/Loss']}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="profit" 
                    stroke="#00ff88" 
                    strokeWidth={2}
                    dot={{ fill: '#00ff88', strokeWidth: 2, r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="no-data-chart">
                <BarChart3 size={48} className="no-data-icon" />
                <p>No trading data available yet</p>
                <small>Performance chart will appear when trades are executed</small>
              </div>
            )}
          </div>
        </div>

        {/* Recent Signals */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Recent Signals</h3>
            <div className="signal-count">
              <Zap size={16} />
              {botStatus.signals?.length || 0} total
            </div>
          </div>
          <div className="signals-list">
            {getRecentSignals().length > 0 ? (
              getRecentSignals().map((signal, index) => (
                <div key={index} className="signal-item">
                  <div className={`signal-direction ${signal.direction?.toLowerCase()}`}>
                    {signal.direction === 'BUY' ? (
                      <TrendingUp size={16} />
                    ) : (
                      <TrendingDown size={16} />
                    )}
                    {signal.direction}
                  </div>
                  <div className="signal-symbol">{signal.symbol}</div>
                  <div className="signal-time">
                    {signal.timestamp ? new Date(signal.timestamp).toLocaleTimeString() : 'Now'}
                  </div>
                </div>
              ))
            ) : (
              <div className="no-signals">
                <Activity size={24} className="no-signals-icon" />
                <p>No signals generated yet</p>
                <small>Signals will appear when the bot detects trading opportunities</small>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Symbol Performance */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <PieChart size={20} style={{ marginRight: '8px' }} />
            Performance by Symbol
          </h3>
          <div className="symbol-count">
            {symbolStats.length} symbols traded
          </div>
        </div>
        <div className="symbol-stats-table">
          {symbolStats.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Trades</th>
                  <th>Win Rate</th>
                  <th>Wins/Losses</th>
                  <th>Total P&L</th>
                  <th>Avg Win</th>
                  <th>Avg Loss</th>
                  <th>Profit Factor</th>
                </tr>
              </thead>
              <tbody>
                {symbolStats.map((stat, index) => (
                  <tr key={index} className={stat.total_profit >= 0 ? 'profit-row' : 'loss-row'}>
                    <td className="symbol-name">{stat.symbol}</td>
                    <td>{stat.total_trades}</td>
                    <td>
                      <span className={`win-rate ${stat.win_rate >= 50 ? 'good' : stat.win_rate >= 30 ? 'medium' : 'bad'}`}>
                        {stat.win_rate.toFixed(1)}%
                      </span>
                    </td>
                    <td>
                      <span className="wins-losses">
                        <span className="wins">{stat.wins}W</span>
                        <span className="separator">/</span>
                        <span className="losses">{stat.losses}L</span>
                      </span>
                    </td>
                    <td className={stat.total_profit >= 0 ? 'profit' : 'loss'}>
                      {formatCurrency(stat.total_profit)}
                    </td>
                    <td className="avg-win">{formatCurrency(stat.avg_win)}</td>
                    <td className="avg-loss">{formatCurrency(stat.avg_loss)}</td>
                    <td>
                      <span className={`profit-factor ${stat.profit_factor >= 1 ? 'good' : 'bad'}`}>
                        {stat.profit_factor.toFixed(2)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="no-data">
              <PieChart size={48} className="no-data-icon" />
              <p>No symbol statistics available yet</p>
              <small>Statistics will appear after trades are executed</small>
            </div>
          )}
        </div>
      </div>

      {/* Bot Status and Messages */}
      <div className="grid grid-2">
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Bot Status</h3>
            <div className={`status-indicator ${botStatus.isRunning ? 'status-running' : 'status-stopped'}`}>
              {botStatus.isRunning ? 'Running' : 'Stopped'}
            </div>
          </div>
          <div className="status-details">
            <div className="status-item">
              <span className="status-label">Account:</span>
              <span className="status-value">{botStatus.account || 'Not connected'}</span>
            </div>
            <div className="status-item">
              <span className="status-label">Server:</span>
              <span className="status-value">{botStatus.server || 'Unknown'}</span>
            </div>
            <div className="status-item">
              <span className="status-label">Last Update:</span>
              <span className="status-value">
                {botStatus.lastUpdate 
                  ? new Date(botStatus.lastUpdate).toLocaleTimeString()
                  : 'Never'
                }
              </span>
            </div>
            <div className="status-item">
              <span className="status-label">Free Margin:</span>
              <span className="status-value">{formatCurrency(botStatus.freeMargin)}</span>
            </div>
            <div className="status-item">
              <span className="status-label">Equity:</span>
              <span className="status-value">{formatCurrency(botStatus.equity)}</span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title">System Messages</h3>
            {botStatus.errors?.length > 0 && (
              <div className="error-indicator">
                <AlertTriangle size={16} />
                {botStatus.errors.length} errors
              </div>
            )}
          </div>
          <div className="messages-list">
            {messages.length > 0 ? (
              messages.slice(-5).reverse().map((message) => (
                <div key={message.id} className={`message-item message-${message.type}`}>
                  <div className="message-content">{message.text}</div>
                  <div className="message-time">
                    {new Date().toLocaleTimeString()}
                  </div>
                </div>
              ))
            ) : (
              <div className="no-messages">
                <p>No recent messages</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;