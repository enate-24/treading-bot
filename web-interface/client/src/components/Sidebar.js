import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  BarChart3, 
  Settings, 
  FileText, 
  Activity,
  TrendingUp,
  Zap,
  Circle
} from 'lucide-react';
import './Sidebar.css';

const Sidebar = ({ botStatus }) => {
  const location = useLocation();

  const menuItems = [
    { path: '/', icon: BarChart3, label: 'Dashboard' },
    { path: '/performance', icon: TrendingUp, label: 'Performance' },
    { path: '/configuration', icon: Settings, label: 'Configuration' },
    { path: '/logs', icon: FileText, label: 'Logs' }
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <Zap className="logo-icon" />
          <span className="logo-text">HFT Monitor</span>
        </div>
        
        <div className="bot-status">
          <div className={`status-dot ${botStatus.isRunning ? 'running' : 'stopped'}`}>
            <Circle size={8} />
          </div>
          <span className="status-text">
            {botStatus.isRunning ? 'Running' : 'Stopped'}
          </span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;
          
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon size={20} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="quick-stats">
          <div className="stat">
            <span className="stat-label">Balance</span>
            <span className="stat-value">${botStatus.balance?.toFixed(2) || '0.00'}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Positions</span>
            <span className="stat-value">{botStatus.openPositions || 0}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Strategy</span>
            <span className="stat-value">{botStatus.strategy?.toUpperCase() || 'HFT'}</span>
          </div>
        </div>
        
        <div className="activity-indicator">
          <Activity size={16} className={botStatus.isRunning ? 'pulse' : ''} />
          <span className="activity-text">
            {botStatus.lastUpdate 
              ? `Updated ${new Date(botStatus.lastUpdate).toLocaleTimeString()}`
              : 'No updates'
            }
          </span>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;