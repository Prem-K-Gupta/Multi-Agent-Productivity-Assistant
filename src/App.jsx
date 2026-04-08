import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import StatusBar from './components/StatusBar';
import './App.css';

const API_BASE = import.meta.env.DEV ? 'http://127.0.0.1:8000' : '';

function App() {
  const [health, setHealth] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [googleAuth, setGoogleAuth] = useState(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`);
        setHealth(await res.json());
      } catch {
        setHealth({ status: 'offline', db_connected: false, mcp_active: false, google_connected: false, gemini_enabled: false, agents: {} });
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 20000);
    return () => clearInterval(interval);
  }, []);

  // Check Google auth status
  useEffect(() => {
    const checkGoogleAuth = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/auth/google/status?user_id=local_dev`);
        setGoogleAuth(await res.json());
      } catch {
        setGoogleAuth(null);
      }
    };
    checkGoogleAuth();

    // Handle OAuth callback params
    const params = new URLSearchParams(window.location.search);
    if (params.get('auth_success') === 'true') {
      checkGoogleAuth();
      window.history.replaceState({}, '', '/');
    } else if (params.get('auth_error')) {
      window.history.replaceState({}, '', '/');
    }
  }, []);

  return (
    <div className="app-layout">
      <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} health={health} googleAuth={googleAuth} />
      <div className="main-area">
        <StatusBar health={health} onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} sidebarOpen={sidebarOpen} />
        <ChatInterface />
      </div>
    </div>
  );
}

export default App;
