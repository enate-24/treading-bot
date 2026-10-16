import React, { useState, useEffect, useRef } from 'react';
import { 
  FileText, 
  Download, 
  Trash2, 
  Filter,
  Search,
  AlertTriangle,
  Info,
  CheckCircle,
  XCircle,
  Zap
} from 'lucide-react';
import './Logs.css';

const Logs = ({ botStatus, realtimeData }) => {
  const [logs, setLogs] = useState([]);
  const [filteredLogs, setFilteredLogs] = useState([]);
  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const logsEndRef = useRef(null);

  // Fetch REAL logs from server - NO MORE FAKE DATA
  useEffect(() => {
    const fetchRealLogs = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/logs');
        if (response.ok) {
          const realLogs = await response.json();
          setLogs(realLogs);
        } else {
          // If no logs available, show empty state
          setLogs([]);
        }
      } catch (error) {
        console.error('Error fetching logs:', error);
        setLogs([]);
      }
    };

    // Fetch logs immediately
    fetchRealLogs();

    // Fetch logs every 5 seconds
    const interval = setInterval(fetchRealLogs, 5000);

    return () => clearInterval(interval);
  }, []);

  // Filter and search logs
  useEffect(() => {
    let filtered = logs;

    // Apply type filter
    if (filter !== 'all') {
      filtered = filtered.filter(log => log.type.toLowerCase() === filter.toLowerCase());
    }

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(log => 
        log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.source.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    setFilteredLogs(filtered);
  }, [logs, filter, searchTerm]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [filteredLogs, autoScroll]);

  const getLogIcon = (type) => {
    switch (type.toLowerCase()) {
      case 'error':
        return <XCircle size={16} className="text-red" />;
      case 'warning':
        return <AlertTriangle size={16} className="text-yellow" />;
      case 'success':
        return <CheckCircle size={16} className="text-green" />;
      case 'info':
      default:
        return <Info size={16} className="text-blue" />;
    }
  };

  const getLogTypeClass = (type) => {
    switch (type.toLowerCase()) {
      case 'error':
        return 'log-error';
      case 'warning':
        return 'log-warning';
      case 'success':
        return 'log-success';
      case 'info':
      default:
        return 'log-info';
    }
  };

  const handleDownloadLogs = () => {
    const logText = filteredLogs.map(log => {
      // Handle timestamp - it's already a string from the API
      const timestamp = typeof log.timestamp === 'string' ? log.timestamp : new Date(log.timestamp).toISOString();
      return `${timestamp} [${log.type}] ${log.source}: ${log.message}`;
    }).join('\n');

    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `hft_bot_logs_${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleClearLogs = () => {
    setLogs([]);
    setFilteredLogs([]);
  };

  const getLogStats = () => {
    const stats = {
      total: logs.length,
      info: logs.filter(log => log.type.toLowerCase() === 'info').length,
      warning: logs.filter(log => log.type.toLowerCase() === 'warning').length,
      error: logs.filter(log => log.type.toLowerCase() === 'error').length,
      success: logs.filter(log => log.type.toLowerCase() === 'success').length
    };
    return stats;
  };

  const stats = getLogStats();

  return (
    <div className="logs">
      <div className="logs-header">
        <h1>System Logs</h1>
        <div className="logs-actions">
          <button className="btn btn-secondary" onClick={handleDownloadLogs}>
            <Download size={16} />
            Download
          </button>
          <button className="btn btn-danger" onClick={handleClearLogs}>
            <Trash2 size={16} />
            Clear
          </button>
        </div>
      </div>

      {/* Log Statistics */}
      <div className="grid grid-4">
        <div className="card log-stat">
          <div className="stat-header">
            <FileText className="stat-icon text-blue" />
            <span className="stat-title">Total Logs</span>
          </div>
          <div className="stat-value">{stats.total}</div>
        </div>

        <div className="card log-stat">
          <div className="stat-header">
            <Info className="stat-icon text-blue" />
            <span className="stat-title">Info</span>
          </div>
          <div className="stat-value text-blue">{stats.info}</div>
        </div>

        <div className="card log-stat">
          <div className="stat-header">
            <AlertTriangle className="stat-icon text-yellow" />
            <span className="stat-title">Warnings</span>
          </div>
          <div className="stat-value text-yellow">{stats.warning}</div>
        </div>

        <div className="card log-stat">
          <div className="stat-header">
            <XCircle className="stat-icon text-red" />
            <span className="stat-title">Errors</span>
          </div>
          <div className="stat-value text-red">{stats.error}</div>
        </div>
      </div>

      {/* Log Controls */}
      <div className="card">
        <div className="log-controls">
          <div className="search-container">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search logs..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
          </div>

          <div className="filter-container">
            <Filter size={16} className="filter-icon" />
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="filter-select"
            >
              <option value="all">All Types</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
              <option value="success">Success</option>
            </select>
          </div>

          <div className="auto-scroll-container">
            <label className="auto-scroll-label">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
              />
              Auto-scroll
            </label>
          </div>

          <div className="log-count">
            Showing {filteredLogs.length} of {logs.length} logs
          </div>
        </div>
      </div>

      {/* Log Display */}
      <div className="card logs-container">
        <div className="logs-header-bar">
          <h3 className="logs-title">
            <Zap size={20} />
            Real-time Logs
          </h3>
          <div className="logs-status">
            <div className={`status-dot ${botStatus.isRunning ? 'running' : 'stopped'}`}></div>
            {botStatus.isRunning ? 'Live' : 'Stopped'}
          </div>
        </div>

        <div className="logs-content">
          {filteredLogs.length > 0 ? (
            <>
              {filteredLogs.map((log) => {
                // Handle timestamp - convert string to Date if needed
                const timestamp = typeof log.timestamp === 'string' 
                  ? new Date(log.timestamp).toLocaleString()
                  : log.timestamp.toLocaleString();
                
                return (
                  <div key={log.id} className={`log-entry ${getLogTypeClass(log.type)}`}>
                    <div className="log-timestamp">
                      {timestamp}
                    </div>
                    <div className="log-type">
                      {getLogIcon(log.type)}
                      <span className="log-type-text">{log.type}</span>
                    </div>
                    <div className="log-source">
                      {log.source}
                    </div>
                    <div className="log-message">
                      {log.message}
                    </div>
                  </div>
                );
              })}
              <div ref={logsEndRef} />
            </>
          ) : (
            <div className="no-logs">
              <FileText size={48} className="no-logs-icon" />
              <h3>No logs found</h3>
              <p>
                {searchTerm || filter !== 'all' 
                  ? 'Try adjusting your search or filter criteria'
                  : 'Logs will appear here when the bot is running'
                }
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Logs;