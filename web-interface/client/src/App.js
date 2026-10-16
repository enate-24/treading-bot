import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import io from 'socket.io-client';
import Dashboard from './components/Dashboard';
import Sidebar from './components/Sidebar';
import Performance from './components/Performance';
import Configuration from './components/Configuration';
import Logs from './components/Logs';
import './App.css';

const socket = io('http://localhost:5000');

function App() {
  const [botStatus, setBotStatus] = useState({
    isRunning: false,
    lastUpdate: null,
    totalTrades: 0,
    openPositions: 0,
    balance: 0,
    equity: 0,
    profit: 0,
    winRate: 0,
    strategy: 'hft',
    signals: [],
    errors: []
  });

  const [realtimeData, setRealtimeData] = useState({
    prices: {},
    signals: [],
    trades: [],
    performance: {
      hourly: [],
      daily: []
    }
  });

  const [messages, setMessages] = useState([]);
  const [currentPage, setCurrentPage] = useState('dashboard');

  useEffect(() => {
    // Socket event listeners
    socket.on('botStatus', (status) => {
      setBotStatus(status);
    });

    socket.on('realtimeData', (data) => {
      setRealtimeData(data);
    });

    socket.on('performanceUpdate', (performance) => {
      setRealtimeData(prev => ({
        ...prev,
        performance
      }));
    });

    socket.on('message', (message) => {
      setMessages(prev => [...prev, { ...message, id: Date.now() }].slice(-10));
    });

    // Cleanup
    return () => {
      socket.off('botStatus');
      socket.off('realtimeData');
      socket.off('performanceUpdate');
      socket.off('message');
    };
  }, []);

  const handleStartBot = (config = {}) => {
    socket.emit('startBot', config);
  };

  const handleStopBot = () => {
    socket.emit('stopBot');
  };

  const handleConfigUpdate = (configData) => {
    socket.emit('updateConfig', configData);
  };

  return (
    <Router>
      <div className="app">
        <Sidebar 
          currentPage={currentPage} 
          setCurrentPage={setCurrentPage}
          botStatus={botStatus}
        />
        
        <main className="main-content">
          <Routes>
            <Route 
              path="/" 
              element={
                <Dashboard 
                  botStatus={botStatus}
                  realtimeData={realtimeData}
                  onStartBot={handleStartBot}
                  onStopBot={handleStopBot}
                  messages={messages}
                />
              } 
            />
            <Route 
              path="/performance" 
              element={
                <Performance 
                  botStatus={botStatus}
                  realtimeData={realtimeData}
                />
              } 
            />
            <Route 
              path="/configuration" 
              element={
                <Configuration 
                  onConfigUpdate={handleConfigUpdate}
                  socket={socket}
                />
              } 
            />
            <Route 
              path="/logs" 
              element={
                <Logs 
                  botStatus={botStatus}
                  realtimeData={realtimeData}
                />
              } 
            />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;