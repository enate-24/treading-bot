import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Target,
  BarChart3,
  PieChart,
  Calendar,
  Filter,
  Activity,
  AlertCircle,
  Award
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';
import './Performance.css';

const Performance = () => {
  const [timeframe, setTimeframe] = useState('hourly');
  const [selectedMetric, setSelectedMetric] = useState('profit');
  const [performanceData, setPerformanceData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPerformanceData();
    const interval = setInterval(fetchPerformanceData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchPerformanceData = async () => {
    try {
      const response = await fetch('/api/performance-data');
      const data = await response.json();
      setPerformanceData(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching performance data:', error);
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(value || 0);
  };

  const formatPercentage = (value) => {
    return `${((value || 0) * 100).toFixed(1)}%`;
  };

  const getChartData = () => {
    if (!performanceData) return [];
    return timeframe === 'hourly' ? performanceData.hourly : performanceData.daily;
  };

  const getSymbolDistribution = () => {
    if (!performanceData || !performanceData.symbols) return [];
    
    const colors = ['#00ff88', '#4488ff', '#ffaa00', '#ff4444', '#aa44ff', '#44ffff'];
    return performanceData.symbols.map((item, index) => ({
      name: item.symbol,
      value: item.trades,
      color: colors[index % colors.length]
    }));
  };

  if (loading) {
    return (
      <div className="performance loading-state">
        <Activity size={48} className="loading-icon" />
        <p>Loading performance data...</p>
      </div>
    );
  }

  if (!performanceData || !performanceData.overall) {
    return (
      <div className="performance error-state">
        <AlertCircle size={48} className="error-icon" />
        <p>No performance data available</p>
        <small>Start trading to see performance metrics</small>
      </div>
    );
  }

  const overall = performanceData.overall;
  const account = performanceData.account;

  return (
    <div className="performance">
      <div className="performance-header">
        <div>
          <h1>Performance Analytics</h1>
          <p className="performance-subtitle">Comprehensive trading performance analysis</p>
        </div>
        <div className="performance-controls">
          <div className="timeframe-selector">
            <button 
              className={`timeframe-btn ${timeframe === 'hourly' ? 'active' : ''}`}
              onClick={() => setTimeframe('hourly')}
            >
              <Calendar size={16} />
              Hourly
            </button>
            <button 
              className={`timeframe-btn ${timeframe === 'daily' ? 'active' : ''}`}
              onClick={() => setTimeframe('daily')}
            >
              <Calendar size={16} />
              Daily
            </button>
          </div>
        </div>
      </div>

      {/* Key Performance Metrics */}
      <div className="grid grid-4">
        <div className="card metric-card">
          <div className="metric-header">
            <DollarSign className="metric-icon text-green" />
            <span className="metric-title">Total Profit/Loss</span>
          </div>
          <div className={`metric-value ${overall.total_profit >= 0 ? 'metric-positive' : 'metric-negative'}`}>
            {formatCurrency(overall.total_profit)}
          </div>
          <div className="metric-change">
            <span className={overall.total_profit >= 0 ? 'text-green' : 'text-red'}>
              {overall.total_profit >= 0 ? '+' : ''}{((overall.total_profit / 10) * 100).toFixed(1)}%
            </span>
            {' '}from start
          </div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <BarChart3 className="metric-icon text-blue" />
            <span className="metric-title">Total Trades</span>
          </div>
          <div className="metric-value metric-neutral">
            {overall.total_trades}
          </div>
          <div className="metric-change">
            <span className="text-green">{overall.winning_trades}W</span>
            {' / '}
            <span className="text-red">{overall.losing_trades}L</span>
          </div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <Target className={`metric-icon ${overall.win_rate >= 0.5 ? 'text-green' : 'text-red'}`} />
            <span className="metric-title">Win Rate</span>
          </div>
          <div className={`metric-value ${overall.win_rate >= 0.5 ? 'metric-positive' : 'metric-negative'}`}>
            {formatPercentage(overall.win_rate)}
          </div>
          <div className="metric-change">
            Target: 50%+ {overall.win_rate >= 0.5 ? '✓' : '✗'}
          </div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <Award className={`metric-icon ${overall.profit_factor >= 1 ? 'text-green' : 'text-red'}`} />
            <span className="metric-title">Profit Factor</span>
          </div>
          <div className={`metric-value ${overall.profit_factor >= 1 ? 'metric-positive' : 'metric-negative'}`}>
            {overall.profit_factor.toFixed(2)}
          </div>
          <div className="metric-change">
            {overall.profit_factor >= 1 ? 'Profitable' : 'Losing'} strategy
          </div>
        </div>
      </div>

      <div className="grid grid-2">
        {/* Performance Chart */}
        <div className="card chart-card">
          <div className="card-header">
            <h3 className="card-title">
              {selectedMetric === 'profit' && 'Profit/Loss Trend'}
              {selectedMetric === 'trades' && 'Trading Activity'}
              {selectedMetric === 'winRate' && 'Win Rate Trend'}
            </h3>
            <div className="chart-controls">
              <select 
                value={selectedMetric} 
                onChange={(e) => setSelectedMetric(e.target.value)}
                className="metric-select"
              >
                <option value="profit">Profit/Loss</option>
                <option value="trades">Trade Count</option>
                <option value="winRate">Win Rate</option>
              </select>
            </div>
          </div>
          <div className="chart-container">
            {getChartData().length > 0 ? (
              <ResponsiveContainer width="100%" height={350}>
                {selectedMetric === 'profit' ? (
                  <AreaChart data={getChartData()}>
                    <defs>
                      <linearGradient id="profitGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#00ff88" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#00ff88" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="lossGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ff4444" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#ff4444" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                    <XAxis 
                      dataKey="timestamp" 
                      tickFormatter={(value) => {
                        const date = new Date(value);
                        return timeframe === 'hourly' 
                          ? date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                          : date.toLocaleDateString([], { month: 'short', day: 'numeric' });
                      }}
                      stroke="#888888"
                    />
                    <YAxis stroke="#888888" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'rgba(0,0,0,0.9)', 
                        border: '1px solid rgba(255,255,255,0.2)',
                        borderRadius: '8px'
                      }}
                      formatter={(value) => [formatCurrency(value), 'P&L']}
                      labelFormatter={(value) => new Date(value).toLocaleString()}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="profit" 
                      stroke="#00ff88" 
                      strokeWidth={2}
                      fillOpacity={1} 
                      fill="url(#profitGradient)" 
                    />
                  </AreaChart>
                ) : selectedMetric === 'trades' ? (
                  <BarChart data={getChartData()}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                    <XAxis 
                      dataKey="timestamp" 
                      tickFormatter={(value) => {
                        const date = new Date(value);
                        return timeframe === 'hourly' 
                          ? date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                          : date.toLocaleDateString([], { month: 'short', day: 'numeric' });
                      }}
                      stroke="#888888"
                    />
                    <YAxis stroke="#888888" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'rgba(0,0,0,0.9)', 
                        border: '1px solid rgba(255,255,255,0.2)',
                        borderRadius: '8px'
                      }}
                      formatter={(value) => [value, 'Trades']}
                      labelFormatter={(value) => new Date(value).toLocaleString()}
                    />
                    <Bar dataKey="trades" fill="#4488ff" radius={[4, 4, 0, 0]} />
                  </BarChart>
                ) : (
                  <LineChart data={getChartData()}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                    <XAxis 
                      dataKey="timestamp" 
                      tickFormatter={(value) => {
                        const date = new Date(value);
                        return timeframe === 'hourly' 
                          ? date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                          : date.toLocaleDateString([], { month: 'short', day: 'numeric' });
                      }}
                      stroke="#888888"
                    />
                    <YAxis 
                      stroke="#888888"
                      tickFormatter={(value) => formatPercentage(value)}
                    />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'rgba(0,0,0,0.9)', 
                        border: '1px solid rgba(255,255,255,0.2)',
                        borderRadius: '8px'
                      }}
                      formatter={(value) => [formatPercentage(value), 'Win Rate']}
                      labelFormatter={(value) => new Date(value).toLocaleString()}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="winRate" 
                      stroke="#ffaa00" 
                      strokeWidth={3}
                      dot={{ fill: '#ffaa00', strokeWidth: 2, r: 5 }}
                    />
                  </LineChart>
                )}
              </ResponsiveContainer>
            ) : (
              <div className="no-data-chart">
                <BarChart3 size={48} className="no-data-icon" />
                <p>No {timeframe} data available</p>
              </div>
            )}
          </div>
        </div>

        {/* Trade Distribution */}
        <div className="card chart-card">
          <div className="card-header">
            <h3 className="card-title">
              <PieChart size={20} style={{ marginRight: '8px' }} />
              Trade Distribution by Symbol
            </h3>
          </div>
          <div className="chart-container">
            {getSymbolDistribution().length > 0 ? (
              <ResponsiveContainer width="100%" height={350}>
                <RechartsPieChart>
                  <Pie
                    data={getSymbolDistribution()}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {getSymbolDistribution().map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(0,0,0,0.9)', 
                      border: '1px solid rgba(255,255,255,0.2)',
                      borderRadius: '8px'
                    }}
                    formatter={(value) => [value, 'Trades']}
                  />
                </RechartsPieChart>
              </ResponsiveContainer>
            ) : (
              <div className="no-data-chart">
                <PieChart size={48} className="no-data-icon" />
                <p>No symbol data available</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Detailed Statistics */}
      <div className="grid grid-3">
        <div className="card stats-card">
          <div className="card-header">
            <h3 className="card-title">
              <TrendingUp size={20} style={{ marginRight: '8px' }} />
              Win/Loss Analysis
            </h3>
          </div>
          <div className="stats-list">
            <div className="stat-item">
              <span className="stat-label">Total Trades:</span>
              <span className="stat-value">{overall.total_trades}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Winning Trades:</span>
              <span className="stat-value text-green">{overall.winning_trades}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Losing Trades:</span>
              <span className="stat-value text-red">{overall.losing_trades}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Win Rate:</span>
              <span className={`stat-value ${overall.win_rate >= 0.5 ? 'text-green' : 'text-red'}`}>
                {formatPercentage(overall.win_rate)}
              </span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Best Trade:</span>
              <span className="stat-value text-green">{formatCurrency(overall.best_trade)}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Worst Trade:</span>
              <span className="stat-value text-red">{formatCurrency(overall.worst_trade)}</span>
            </div>
          </div>
        </div>

        <div className="card stats-card">
          <div className="card-header">
            <h3 className="card-title">
              <DollarSign size={20} style={{ marginRight: '8px' }} />
              Profit Metrics
            </h3>
          </div>
          <div className="stats-list">
            <div className="stat-item">
              <span className="stat-label">Total Profit:</span>
              <span className={`stat-value ${overall.total_profit >= 0 ? 'text-green' : 'text-red'}`}>
                {formatCurrency(overall.total_profit)}
              </span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Total Wins:</span>
              <span className="stat-value text-green">{formatCurrency(overall.total_wins)}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Total Losses:</span>
              <span className="stat-value text-red">{formatCurrency(-overall.total_losses)}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Average Win:</span>
              <span className="stat-value text-green">{formatCurrency(overall.avg_win)}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Average Loss:</span>
              <span className="stat-value text-red">{formatCurrency(overall.avg_loss)}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Expectancy:</span>
              <span className={`stat-value ${overall.expectancy >= 0 ? 'text-green' : 'text-red'}`}>
                {formatCurrency(overall.expectancy)}
              </span>
            </div>
          </div>
        </div>

        <div className="card stats-card">
          <div className="card-header">
            <h3 className="card-title">
              <Target size={20} style={{ marginRight: '8px' }} />
              Risk Metrics
            </h3>
          </div>
          <div className="stats-list">
            <div className="stat-item">
              <span className="stat-label">Profit Factor:</span>
              <span className={`stat-value ${overall.profit_factor >= 1 ? 'text-green' : 'text-red'}`}>
                {overall.profit_factor.toFixed(2)}
              </span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Max Drawdown:</span>
              <span className="stat-value text-red">{overall.max_drawdown.toFixed(2)}%</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Sharpe Ratio:</span>
              <span className="stat-value">{overall.sharpe_ratio.toFixed(2)}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Recovery Factor:</span>
              <span className="stat-value">{overall.recovery_factor.toFixed(2)}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Calmar Ratio:</span>
              <span className="stat-value">{overall.calmar_ratio.toFixed(2)}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Current Balance:</span>
              <span className="stat-value">{formatCurrency(account.balance)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Trades */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <Activity size={20} style={{ marginRight: '8px' }} />
            Recent Trades
          </h3>
          <span className="trades-count">{performanceData.trades?.length || 0} trades</span>
        </div>
        <div className="trades-table-container">
          {performanceData.trades && performanceData.trades.length > 0 ? (
            <table className="trades-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Symbol</th>
                  <th>Type</th>
                  <th>Volume</th>
                  <th>Profit/Loss</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {performanceData.trades.map((trade, index) => (
                  <tr key={index} className={trade.profit >= 0 ? 'win-row' : 'loss-row'}>
                    <td>{new Date(trade.time).toLocaleString()}</td>
                    <td className="symbol-cell">{trade.symbol}</td>
                    <td>
                      <span className={`trade-type ${trade.type.toLowerCase()}`}>
                        {trade.type}
                      </span>
                    </td>
                    <td>{trade.volume}</td>
                    <td className={trade.profit >= 0 ? 'profit-cell' : 'loss-cell'}>
                      {formatCurrency(trade.profit)}
                    </td>
                    <td>
                      <span className={`result-badge ${trade.profit >= 0 ? 'win' : 'loss'}`}>
                        {trade.profit >= 0 ? 'WIN' : 'LOSS'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="no-data">
              <Activity size={48} className="no-data-icon" />
              <p>No recent trades</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Performance;
