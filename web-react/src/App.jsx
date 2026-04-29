import { useState, useEffect } from 'react';
import ChatTimeline from './components/ChatTimeline';
import ChatInput from './components/ChatInput';
import AuthDialog from './components/AuthDialog';
import { chat, listChatSessions, getChatSession, getMe } from './api';
import './App.css';

export default function App() {
  const [user, setUser] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);  // chat timeline
  const [loading, setLoading] = useState(false);
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState('signup');
  const [showUserMenu, setShowUserMenu] = useState(false);

  const GITHUB_URL = 'https://github.com/maris205/open-rosalind';

  useEffect(() => {
    loadUser();
    loadSessions();
  }, []);

  useEffect(() => {
    if (user) loadSessions();
  }, [user]);

  async function loadUser() {
    if (localStorage.getItem('or_token')) {
      const me = await getMe();
      if (me) setUser(me);
      else localStorage.removeItem('or_token');
    }
  }

  async function loadSessions() {
    try {
      const data = await listChatSessions();
      setSessions(data.sessions || []);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  }

  async function handleSend(text) {
    // Add user message immediately
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setLoading(true);

    try {
      const result = await chat(text, currentSessionId);

      // Update session_id if this is a new conversation
      if (!currentSessionId && result.session_id) {
        setCurrentSessionId(result.session_id);
      }

      // Add assistant message
      setMessages((prev) => [...prev, {
        role: 'assistant',
        ...result,
      }]);

      // Refresh sessions list (works for both authenticated and anonymous now)
      await loadSessions();
    } catch (err) {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        summary: `❌ Error: ${err.message}`,
        execution_mode: 'error',
        execution_reason: err.message,
      }]);
    } finally {
      setLoading(false);
    }
  }

  async function handleNewSession() {
    if (!user) {
      // Anonymous can only have one session
      setAuthMode('signup');
      setShowAuth(true);
      return;
    }
    setMessages([]);
    setCurrentSessionId(null);
  }

  async function handleLoadSession(session) {
    try {
      const data = await getChatSession(session.session_id);
      setCurrentSessionId(session.session_id);

      // Rebuild full chat timeline from stored messages
      const msgs = data.messages || [];
      if (msgs.length > 0) {
        setMessages(msgs.map((m) => {
          if (m.role === 'user') {
            return { role: 'user', content: m.content };
          } else {
            // Assistant: spread the saved card so all UI fields work
            return { role: 'assistant', ...(m.card || {}), summary: m.content || (m.card?.summary || '') };
          }
        }));
      } else {
        // Fallback for legacy sessions saved without messages
        setMessages([
          { role: 'user', content: data.user_input },
          {
            role: 'assistant',
            summary: data.summary,
            skill: data.skill,
            confidence: data.confidence,
            annotation: data.annotation,
            evidence: data.evidence,
            notes: data.notes,
            execution_mode: data.execution_mode,
            execution_reason: data.execution_reason,
            trace_steps: [],
          },
        ]);
      }
    } catch (err) {
      alert(`Failed to load session: ${err.message}`);
    }
  }

  function handleLogout() {
    localStorage.removeItem('or_token');
    localStorage.removeItem('or_email');
    localStorage.removeItem('or_anon_token');
    setUser(null);
    setSessions([]);
    setMessages([]);
    setCurrentSessionId(null);
  }

  function handleAuthSuccess(result) {
    setUser({ user_id: result.user_id, email: result.email, is_anonymous: false });
    setShowAuth(false);
    // After signup/login, start fresh: clear anonymous messages + session
    // so the user enters a clean "logged-in" state ready for new conversations.
    setMessages([]);
    setCurrentSessionId(null);
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>🧬 Open-Rosalind</h1>
          <p className="sidebar-tagline">Bio-agent</p>
        </div>

        <button className="btn-new-session" onClick={handleNewSession}>
          + New conversation
        </button>

        <div className="sidebar-section">
          <div className="sidebar-label">Sessions</div>
          {sessions.length === 0 ? (
            <div className="sidebar-empty">
              {user ? 'No sessions yet' : 'Sign in to save sessions'}
            </div>
          ) : (
            <ul className="session-list">
              {sessions.map((s) => (
                <li
                  key={s.session_id}
                  className={`session-item ${s.session_id === currentSessionId ? 'active' : ''}`}
                  onClick={() => handleLoadSession(s)}
                >
                  <div className="session-title">{(s.user_input || '').slice(0, 50)}</div>
                  <div className="session-meta">
                    {s.execution_mode === 'harness' ? '🔗' : '⚡'} {s.skill || ''}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="sidebar-footer">
          {user ? (
            <div className="user-block">
              <button
                className="user-button"
                onClick={() => setShowUserMenu(!showUserMenu)}
                title={user.email}
              >
                <div className="user-avatar">{user.email.charAt(0).toUpperCase()}</div>
                <div className="user-name">{user.email.split('@')[0]}</div>
                <div className="user-caret">⌄</div>
              </button>
              {showUserMenu && (
                <div className="user-menu" onMouseLeave={() => setShowUserMenu(false)}>
                  <a className="user-menu-item" href={GITHUB_URL} target="_blank" rel="noopener noreferrer">
                    <span className="menu-icon">📖</span> Help / GitHub
                  </a>
                  <button className="user-menu-item" onClick={() => { setShowUserMenu(false); handleLogout(); }}>
                    <span className="menu-icon">↗</span> Log out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="user-block">
              <div className="auth-buttons">
                <button className="btn-link" onClick={() => { setAuthMode('login'); setShowAuth(true); }}>
                  Log in
                </button>
                {' · '}
                <button className="btn-link" onClick={() => { setAuthMode('signup'); setShowAuth(true); }}>
                  Sign up
                </button>
              </div>
              <a className="help-link" href={GITHUB_URL} target="_blank" rel="noopener noreferrer">
                📖 Help
              </a>
            </div>
          )}
        </div>
      </aside>

      <main className="main">
        <ChatTimeline
          messages={messages}
          loading={loading}
          onSignupClick={() => { setAuthMode('signup'); setShowAuth(true); }}
        />
        <ChatInput onSend={handleSend} disabled={loading} />
      </main>

      {showAuth && (
        <AuthDialog
          defaultMode={authMode}
          onClose={() => setShowAuth(false)}
          onSuccess={handleAuthSuccess}
        />
      )}
    </div>
  );
}
