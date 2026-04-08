import React, { useState, useRef, useEffect } from 'react';
import './ChatInterface.css';

const API_BASE = import.meta.env.DEV ? 'http://127.0.0.1:8000' : '';

const SUGGESTIONS = [
  { label: 'Create a task', prompt: 'create task ' },
  { label: 'Show my tasks', prompt: 'show my tasks' },
  { label: 'Schedule meeting', prompt: 'schedule a meeting ' },
  { label: 'Show calendar', prompt: 'show my calendar' },
  { label: 'Take a note', prompt: 'note: ' },
  { label: 'Plan my day', prompt: 'plan my day' },
  { label: 'Check email', prompt: 'check my email' },
  { label: 'Search Drive', prompt: 'search drive for ' },
  { label: 'Remember this', prompt: 'remember that ' },
  { label: 'Recall memories', prompt: 'what do you remember?' },
];

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text) => {
    if (!text.trim() || loading) return;

    setMessages((prev) => [...prev, { id: Date.now(), text, isUser: true }]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, user_id: 'local_dev' }),
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          text: data.response,
          agent: data.active_agent,
          actions: data.actions_taken,
          isUser: false,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          text: 'Could not connect to the backend. Make sure the FastAPI server is running on port 8000.',
          agent: 'System',
          isUser: false,
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleSuggestion = (prompt) => {
    if (prompt.endsWith(' ')) {
      setInput(prompt);
      inputRef.current?.focus();
    } else {
      sendMessage(prompt);
    }
  };

  const showWelcome = messages.length === 0;

  return (
    <div className="chat-wrapper">
      <div className="chat-scroll-area">
        {showWelcome && (
          <div className="welcome">
            <div className="welcome-icon">N</div>
            <h1 className="welcome-title">What can I help you with?</h1>
            <p className="welcome-sub">
              I coordinate 6 AI agents and 7 tools to manage your tasks, calendar, email, notes, and more.
            </p>
            <div className="suggestion-grid">
              {SUGGESTIONS.map((s, i) => (
                <button key={i} className="suggestion-chip" onClick={() => handleSuggestion(s.prompt)}>
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`msg-row ${msg.isUser ? 'msg-user' : 'msg-agent'}`}>
            {!msg.isUser && (
              <div className="msg-avatar">
                <span>N</span>
              </div>
            )}
            <div className={`msg-bubble ${msg.isUser ? 'bubble-user' : 'bubble-agent'} ${msg.isError ? 'bubble-error' : ''}`}>
              {!msg.isUser && msg.agent && (
                <div className="msg-agent-name">{msg.agent}</div>
              )}
              <div className="msg-text">{msg.text}</div>
              {!msg.isUser && msg.actions && msg.actions.length > 0 && (
                <details className="msg-actions-details">
                  <summary className="msg-actions-summary">
                    {msg.actions.length} action{msg.actions.length > 1 ? 's' : ''} performed
                  </summary>
                  <div className="msg-actions-list">
                    {msg.actions.map((a, i) => (
                      <div key={i} className="msg-action-item">{a}</div>
                    ))}
                  </div>
                </details>
              )}
            </div>
            {msg.isUser && (
              <div className="msg-avatar msg-avatar-user">
                <span>U</span>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="msg-row msg-agent">
            <div className="msg-avatar"><span>N</span></div>
            <div className="msg-bubble bubble-agent">
              <div className="thinking">
                <div className="thinking-dots">
                  <span /><span /><span />
                </div>
                <span className="thinking-text">Thinking...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {!showWelcome && messages.length > 0 && (
        <div className="inline-suggestions">
          {SUGGESTIONS.slice(0, 5).map((s, i) => (
            <button key={i} className="inline-chip" onClick={() => handleSuggestion(s.prompt)}>
              {s.label}
            </button>
          ))}
        </div>
      )}

      <form className="chat-form" onSubmit={handleSubmit}>
        <div className="input-wrapper">
          <input
            ref={inputRef}
            type="text"
            className="chat-input"
            placeholder="Message Nexus..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            autoFocus
          />
          <button
            type="submit"
            className={`send-button ${input.trim() && !loading ? 'ready' : ''}`}
            disabled={!input.trim() || loading}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
        <div className="input-hint">
          Nexus can manage tasks, calendar, email, notes & memory. Type <strong>help</strong> for all commands.
        </div>
      </form>
    </div>
  );
};

export default ChatInterface;
