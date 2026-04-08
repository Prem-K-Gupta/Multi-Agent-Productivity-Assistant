import React from 'react';
import './Sidebar.css';

const Sidebar = ({ open, onToggle, health }) => {
  const agents = health?.agents?.sub_agents || [];
  const tools = health?.agents?.mcp_tools || [];

  if (!open) return null;

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
          <span className="footer-value">Gemini 2.5 Pro</span>
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
