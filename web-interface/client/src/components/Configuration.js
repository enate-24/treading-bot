import React, { useState, useEffect } from 'react';
import { 
  Settings, 
  Save, 
  RotateCcw, 
  AlertTriangle,
  CheckCircle,
  Zap,
  Shield,
  TrendingUp
} from 'lucide-react';
import './Configuration.css';

const Configuration = ({ onConfigUpdate, socket }) => {
  const [configs, setConfigs] = useState({
    standard: null,
    hft: null
  });
  const [activeConfig, setActiveConfig] = useState('standard');
  const [unsavedChanges, setUnsavedChanges] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    // Request configuration data
    socket.emit('getConfig');
    
    socket.on('configData', (data) => {
      setConfigs(data);
      setLoading(false);
    });

    socket.on('message', (msg) => {
      if (msg.text.includes('Configuration')) {
        setMessage(msg);
        setTimeout(() => setMessage(null), 3000);
        setUnsavedChanges(false);
      }
    });

    return () => {
      socket.off('configData');
      socket.off('message');
    };
  }, [socket]);

  const getCurrentConfig = () => {
    return configs[activeConfig] || {};
  };

  const updateConfig = (path, value) => {
    const config = { ...getCurrentConfig() };
    const keys = path.split('.');
    let current = config;
    
    for (let i = 0; i < keys.length - 1; i++) {
      if (!current[keys[i]]) current[keys[i]] = {};
      current = current[keys[i]];
    }
    
    current[keys[keys.length - 1]] = value;
    
    setConfigs(prev => ({
      ...prev,
      [activeConfig]: config
    }));
    setUnsavedChanges(true);
  };

  const handleSave = () => {
    onConfigUpdate({
      type: activeConfig,
      config: getCurrentConfig()
    });
  };

  const handleReset = () => {
    socket.emit('getConfig');
    setUnsavedChanges(false);
  };

  if (loading) {
    return (
      <div className="configuration loading">
        <div className="spinner"></div>
        <p>Loading configuration...</p>
      </div>
    );
  }

  const config = getCurrentConfig();
  const tradingConfig = config.trading || {};
  const hftParams = tradingConfig.hft_parameters || {};

  return (
    <div className="configuration">
      <div className="configuration-header">
        <h1>Bot Configuration</h1>
        <div className="config-actions">
          <div className="config-tabs">
            <button 
              className={`config-tab ${activeConfig === 'standard' ? 'active' : ''}`}
              onClick={() => setActiveConfig('standard')}
            >
              <Settings size={16} />
              Standard
            </button>
            <button 
              className={`config-tab ${activeConfig === 'hft' ? 'active' : ''}`}
              onClick={() => setActiveConfig('hft')}
            >
              <Zap size={16} />
              HFT
            </button>
          </div>
          
          <div className="action-buttons">
            <button 
              className="btn btn-secondary" 
              onClick={handleReset}
              disabled={!unsavedChanges}
            >
              <RotateCcw size={16} />
              Reset
            </button>
            <button 
              className="btn btn-primary" 
              onClick={handleSave}
              disabled={!unsavedChanges}
            >
              <Save size={16} />
              Save Changes
            </button>
          </div>
        </div>
      </div>

      {message && (
        <div className={`notification notification-${message.type}`}>
          {message.type === 'success' ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
          {message.text}
        </div>
      )}

      {unsavedChanges && (
        <div className="unsaved-warning">
          <AlertTriangle size={16} />
          You have unsaved changes. Don't forget to save your configuration.
        </div>
      )}

      <div className="grid grid-2">
        {/* Trading Configuration */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <TrendingUp size={20} />
              Trading Settings
            </h3>
          </div>
          <div className="config-section">
            <div className="form-group">
              <label className="form-label">Trading Symbols</label>
              <div className="symbol-list">
                {(tradingConfig.symbols || []).map((symbol, index) => (
                  <div key={index} className="symbol-item">
                    <input
                      type="text"
                      value={symbol}
                      onChange={(e) => {
                        const newSymbols = [...(tradingConfig.symbols || [])];
                        newSymbols[index] = e.target.value;
                        updateConfig('trading.symbols', newSymbols);
                      }}
                      className="form-input"
                    />
                    <button
                      className="btn-remove"
                      onClick={() => {
                        const newSymbols = (tradingConfig.symbols || []).filter((_, i) => i !== index);
                        updateConfig('trading.symbols', newSymbols);
                      }}
                    >
                      ×
                    </button>
                  </div>
                ))}
                <button
                  className="btn btn-secondary btn-add"
                  onClick={() => {
                    const newSymbols = [...(tradingConfig.symbols || []), 'EURUSD'];
                    updateConfig('trading.symbols', newSymbols);
                  }}
                >
                  + Add Symbol
                </button>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Timeframes</label>
              <div className="timeframe-list">
                {(tradingConfig.timeframes || []).map((timeframe, index) => (
                  <div key={index} className="timeframe-item">
                    <select
                      value={timeframe}
                      onChange={(e) => {
                        const newTimeframes = [...(tradingConfig.timeframes || [])];
                        newTimeframes[index] = e.target.value;
                        updateConfig('trading.timeframes', newTimeframes);
                      }}
                      className="form-select"
                    >
                      <option value="M1">M1 (1 Minute)</option>
                      <option value="M5">M5 (5 Minutes)</option>
                      <option value="M15">M15 (15 Minutes)</option>
                      <option value="M30">M30 (30 Minutes)</option>
                      <option value="H1">H1 (1 Hour)</option>
                      <option value="H4">H4 (4 Hours)</option>
                      <option value="D1">D1 (Daily)</option>
                    </select>
                    <button
                      className="btn-remove"
                      onClick={() => {
                        const newTimeframes = (tradingConfig.timeframes || []).filter((_, i) => i !== index);
                        updateConfig('trading.timeframes', newTimeframes);
                      }}
                    >
                      ×
                    </button>
                  </div>
                ))}
                <button
                  className="btn btn-secondary btn-add"
                  onClick={() => {
                    const newTimeframes = [...(tradingConfig.timeframes || []), 'M1'];
                    updateConfig('trading.timeframes', newTimeframes);
                  }}
                >
                  + Add Timeframe
                </button>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Strategy</label>
              <select
                value={tradingConfig.strategy || 'hft'}
                onChange={(e) => updateConfig('trading.strategy', e.target.value)}
                className="form-select"
              >
                <option value="hft">High-Frequency Trading (HFT)</option>
                <option value="scalping">Scalping</option>
                <option value="swing_trading">Swing Trading</option>
              </select>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Max Positions</label>
                <input
                  type="number"
                  value={tradingConfig.max_positions || 5}
                  onChange={(e) => updateConfig('trading.max_positions', parseInt(e.target.value))}
                  className="form-input"
                  min="1"
                  max="20"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Risk per Trade (%)</label>
                <input
                  type="number"
                  value={(tradingConfig.risk_per_trade || 0.005) * 100}
                  onChange={(e) => updateConfig('trading.risk_per_trade', parseFloat(e.target.value) / 100)}
                  className="form-input"
                  min="0.1"
                  max="5"
                  step="0.1"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Risk Management */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <Shield size={20} />
              Risk Management
            </h3>
          </div>
          <div className="config-section">
            <div className="form-group">
              <label className="form-label">Max Drawdown (%)</label>
              <input
                type="number"
                value={(tradingConfig.max_drawdown || 0.05) * 100}
                onChange={(e) => updateConfig('trading.max_drawdown', parseFloat(e.target.value) / 100)}
                className="form-input"
                min="1"
                max="20"
                step="0.5"
              />
              <small className="form-help">Maximum allowed portfolio drawdown</small>
            </div>

            <div className="form-group">
              <label className="form-label">Daily Loss Limit (%)</label>
              <input
                type="number"
                value={(tradingConfig.daily_loss_limit || 0.02) * 100}
                onChange={(e) => updateConfig('trading.daily_loss_limit', parseFloat(e.target.value) / 100)}
                className="form-input"
                min="0.5"
                max="10"
                step="0.5"
              />
              <small className="form-help">Stop trading if daily loss exceeds this limit</small>
            </div>

            <div className="risk-indicators">
              <div className="risk-indicator">
                <span className="risk-label">Risk Level:</span>
                <span className={`risk-value ${tradingConfig.risk_per_trade > 0.01 ? 'high' : tradingConfig.risk_per_trade > 0.005 ? 'medium' : 'low'}`}>
                  {tradingConfig.risk_per_trade > 0.01 ? 'High' : tradingConfig.risk_per_trade > 0.005 ? 'Medium' : 'Low'}
                </span>
              </div>
              <div className="risk-indicator">
                <span className="risk-label">Expected Trades/Day:</span>
                <span className="risk-value">
                  {activeConfig === 'hft' ? '200-500' : activeConfig === 'scalping' ? '50-100' : '5-20'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* HFT Parameters (only show for HFT config) */}
      {activeConfig === 'hft' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <Zap size={20} />
              HFT Parameters
            </h3>
            <div className="hft-badge">
              High-Frequency Trading Configuration
            </div>
          </div>
          <div className="config-section">
            <div className="grid grid-3">
              <div className="form-group">
                <label className="form-label">Tick Threshold</label>
                <input
                  type="number"
                  value={hftParams.tick_threshold || 0.00001}
                  onChange={(e) => updateConfig('trading.hft_parameters.tick_threshold', parseFloat(e.target.value))}
                  className="form-input"
                  min="0.000001"
                  max="0.0001"
                  step="0.000001"
                />
                <small className="form-help">Minimum price movement to consider</small>
              </div>

              <div className="form-group">
                <label className="form-label">Volume Multiplier</label>
                <input
                  type="number"
                  value={hftParams.volume_multiplier || 1.5}
                  onChange={(e) => updateConfig('trading.hft_parameters.volume_multiplier', parseFloat(e.target.value))}
                  className="form-input"
                  min="1.1"
                  max="5.0"
                  step="0.1"
                />
                <small className="form-help">Volume spike threshold multiplier</small>
              </div>

              <div className="form-group">
                <label className="form-label">Mean Reversion Periods</label>
                <input
                  type="number"
                  value={hftParams.mean_reversion_periods || 3}
                  onChange={(e) => updateConfig('trading.hft_parameters.mean_reversion_periods', parseInt(e.target.value))}
                  className="form-input"
                  min="2"
                  max="10"
                />
                <small className="form-help">Number of ticks for mean calculation</small>
              </div>

              <div className="form-group">
                <label className="form-label">Profit Target</label>
                <input
                  type="number"
                  value={hftParams.profit_target || 0.0003}
                  onChange={(e) => updateConfig('trading.hft_parameters.profit_target', parseFloat(e.target.value))}
                  className="form-input"
                  min="0.0001"
                  max="0.001"
                  step="0.0001"
                />
                <small className="form-help">Profit target in price units</small>
              </div>

              <div className="form-group">
                <label className="form-label">Stop Loss</label>
                <input
                  type="number"
                  value={hftParams.stop_loss || 0.0002}
                  onChange={(e) => updateConfig('trading.hft_parameters.stop_loss', parseFloat(e.target.value))}
                  className="form-input"
                  min="0.0001"
                  max="0.001"
                  step="0.0001"
                />
                <small className="form-help">Stop loss in price units</small>
              </div>

              <div className="form-group">
                <label className="form-label">Max Hold Time (seconds)</label>
                <input
                  type="number"
                  value={hftParams.max_hold_time || 180}
                  onChange={(e) => updateConfig('trading.hft_parameters.max_hold_time', parseInt(e.target.value))}
                  className="form-input"
                  min="30"
                  max="600"
                />
                <small className="form-help">Maximum position hold time</small>
              </div>

              <div className="form-group">
                <label className="form-label">Min Confidence</label>
                <input
                  type="number"
                  value={hftParams.min_confidence || 0.3}
                  onChange={(e) => updateConfig('trading.hft_parameters.min_confidence', parseFloat(e.target.value))}
                  className="form-input"
                  min="0.1"
                  max="0.9"
                  step="0.05"
                />
                <small className="form-help">Minimum signal confidence threshold</small>
              </div>

              <div className="form-group">
                <label className="form-label">Spread Threshold</label>
                <input
                  type="number"
                  value={hftParams.spread_threshold || 0.00002}
                  onChange={(e) => updateConfig('trading.hft_parameters.spread_threshold', parseFloat(e.target.value))}
                  className="form-input"
                  min="0.00001"
                  max="0.0001"
                  step="0.00001"
                />
                <small className="form-help">Maximum spread to allow trading</small>
              </div>

              <div className="form-group">
                <label className="form-label">Price Momentum Threshold</label>
                <input
                  type="number"
                  value={hftParams.price_momentum_threshold || 0.00003}
                  onChange={(e) => updateConfig('trading.hft_parameters.price_momentum_threshold', parseFloat(e.target.value))}
                  className="form-input"
                  min="0.00001"
                  max="0.0001"
                  step="0.00001"
                />
                <small className="form-help">Minimum momentum for breakout signals</small>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MetaTrader Connection */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">MetaTrader Connection</h3>
          <div className="connection-status">
            <div className="status-dot running"></div>
            Connected
          </div>
        </div>
        <div className="config-section">
          <div className="connection-info">
            <div className="info-item">
              <span className="info-label">Account:</span>
              <span className="info-value">{config.metatrader?.account || 'Not configured'}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Server:</span>
              <span className="info-value">{config.metatrader?.server || 'Not configured'}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Version:</span>
              <span className="info-value">MT{config.metatrader?.version || 5}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Environment:</span>
              <span className="info-value">{config.environment || 'production'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Configuration;