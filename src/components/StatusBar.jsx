import React from 'react';
import './StatusBar.css';

const StatusBar = ({ health, onToggleSidebar, sidebarOpen }) => {
  const isOnline = health?.status === 'healthy';
  const isDegraded = health?.status === 'degraded';

  return (
    <header className="status-bar">
      <div className="status-bar-left">
        {!sidebarOpen && (
          <button className="menu-btn" onClick={onToggleSidebar} title="Open sidebar">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
        )}
        <div className="status-brand">
          <span className="brand-name">Nexus</span>
          <span className="brand-version">v3.0</span>
        </div>
      </div>

      <div className="status-bar-center">
        <span className="status-label">Multi-Agent Productivity Assistant</span>
      </div>

      <div className="status-bar-right">
        {health && (
          <>
            <div className={`status-chip ${health.gemini_enabled ? 'active' : 'inactive'}`}>
              <span className="chip-dot" />
              Gemini
            </div>
            <div className={`status-chip ${health.google_connected ? 'active' : 'inactive'}`}>
              <span className="chip-dot" />
              Google
            </div>
            <div className={`status-chip ${isOnline ? 'active' : isDegraded ? 'warn' : 'offline'}`}>
              <span className="chip-dot" />
              {health.agents?.total_agents || 0} Agents
            </div>
          </>
        )}
        <div className={`system-status ${isOnline ? 'online' : isDegraded ? 'degraded' : 'offline'}`}>
          <span className="system-dot" />
          {isOnline ? 'Online' : isDegraded ? 'Degraded' : 'Offline'}
        </div>
      </div>
    </header>
  );
};

export default StatusBar;
