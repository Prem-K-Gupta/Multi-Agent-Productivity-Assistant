import React from 'react';
import './Sidebar.css';

const API_BASE = import.meta.env.DEV ? 'http://127.0.0.1:8000' : '';

const Sidebar = ({ open, onToggle, health, googleAuth }) => {
  const agents = health?.agents?.sub_agents || [];
  const tools = health?.agents?.mcp_tools || [];

  if (!open) return null;

  const handleGoogleLogin = () => {
    window.location.href = `${API_BASE}/api/auth/google/login?user_id=local_dev`;
  };

  const handleGoogleLogout = async () => {
    try {
      await fetch(`${API_BASE}/api/auth/google/logout?user_id=local_dev`, { method: 'DELETE' });
      window.location.reload();
    } catch { /* ignore */ }
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="logo-mark">N</div>
          <div>
            <div className="logo-text">Nexus</div>
            <div className="logo-sub">AI Orchestrator</div>
          </div>
        </div>
        <button className="close-btn" onClick={onToggle} title="Close sidebar">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <polyline points="11 17 6 12 11 7"/><line x1="6" y1="12" x2="20" y2="12"/>
          </svg>
        </button>
      </div>

      {/* Google Account */}
      <div className="sidebar-section">
        <div className="section-label">Google Account</div>
        {googleAuth?.authenticated ? (
          <div className="google-account">
            <div className="google-user">
              <span className="google-avatar">
                {(googleAuth.name || googleAuth.email || 'U').charAt(0).toUpperCase()}
              </span>
              <div className="google-info">
                <span className="google-name">{googleAuth.name || 'Connected'}</span>
                <span className="google-email">{googleAuth.email}</span>
              </div>
            </div>
            <button className="google-disconnect" onClick={handleGoogleLogout}>Disconnect</button>
          </div>
        ) : (
          <button className="google-login-btn" onClick={handleGoogleLogin}>
            <svg width="16" height="16" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Sign in with Google
          </button>
        )}
      </div>

      <div className="sidebar-section">
        <div className="section-label">Quick Actions</div>
        <div className="quick-actions">
          <QuickAction icon="+" label="New Task" hint="create task ..." />
          <QuickAction icon="C" label="Calendar" hint="show my calendar" />
          <QuickAction icon="N" label="New Note" hint="note: ..." />
          <QuickAction icon="P" label="Plan Day" hint="plan my day" />
        </div>
      </div>

      <div className="sidebar-section">
        <div className="section-label">Sub-Agents ({agents.length})</div>
        <div className="agent-list">
          {agents.length > 0 ? agents.map((a, i) => (
            <div key={i} className="agent-row">
              <span className="agent-dot" />
              <span className="agent-name">{a.name}</span>
            </div>
          )) : (
            <>
              {['Task Planning', 'Scheduling', 'Context Retrieval', 'Notes', 'Gmail', 'Drive'].map((n, i) => (
                <div key={i} className="agent-row">
                  <span className="agent-dot" />
                  <span className="agent-name">{n} Agent</span>
                </div>
              ))}
            </>
          )}
        </div>
      </div>

      <div className="sidebar-section">
        <div className="section-label">MCP Tools ({tools.length || 7})</div>
        <div className="tool-list">
          {(tools.length > 0 ? tools : [
            { name: 'calendar', description: 'Local calendar' },
            { name: 'task_manager', description: 'Local tasks' },
            { name: 'notes', description: 'Local notes' },
            { name: 'google_calendar', description: 'Google Calendar' },
            { name: 'google_tasks', description: 'Google Tasks' },
            { name: 'gmail', description: 'Gmail' },
            { name: 'google_drive', description: 'Google Drive' },
          ]).map((t, i) => (
            <div key={i} className="tool-row">
              <span className={`tool-icon ${t.name.startsWith('google') || t.name === 'gmail' ? 'google' : 'local'}`}>
                {t.name.startsWith('google') || t.name === 'gmail' ? 'G' : 'L'}
              </span>
              <span className="tool-name">{t.name.replace(/_/g, ' ')}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="sidebar-footer">
        <div className="footer-info">
          <span className="footer-label">Powered by</span>
          <span className="footer-value">Gemini 2.5 Flash</span>
        </div>
      </div>
    </aside>
  );
};

const QuickAction = ({ icon, label, hint }) => (
  <button className="quick-action" title={`Type: "${hint}"`}>
    <span className="qa-icon">{icon}</span>
    <span className="qa-label">{label}</span>
  </button>
);

export default Sidebar;
