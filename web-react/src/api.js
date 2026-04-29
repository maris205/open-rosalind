const API_BASE = '/api';

function authHeaders() {
  const token = localStorage.getItem('or_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

// === Auth ===

export async function signup(email, password) {
  const res = await fetch(`${API_BASE}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function login(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getMe() {
  const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() });
  if (!res.ok) return null;
  return res.json();
}

// === Chat ===

export async function chat(message, sessionId = null) {
  const anonToken = localStorage.getItem('or_anon_token');
  const body = { message };
  if (sessionId) body.session_id = sessionId;
  if (anonToken && !localStorage.getItem('or_token')) body.anon_token = anonToken;

  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  const data = await res.json();
  // Persist anon_token returned for anonymous users
  if (data.anon_token) localStorage.setItem('or_anon_token', data.anon_token);
  return data;
}

export async function listChatSessions() {
  const res = await fetch(`${API_BASE}/chat/sessions`, { headers: authHeaders() });
  if (!res.ok) return { sessions: [] };
  return res.json();
}

export async function getChatSession(sessionId) {
  const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// === Legacy (kept for compatibility) ===

export async function analyze(input, mode = 'auto', followUpSession = null) {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ input, mode, follow_up_session: followUpSession }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function listSessions(limit = 50) {
  const res = await fetch(`${API_BASE}/sessions?limit=${limit}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function getSession(sessionId) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
