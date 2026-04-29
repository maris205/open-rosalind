import { useState } from 'react';
import { signup, login } from '../api';

export default function AuthDialog({ onClose, onSuccess, defaultMode = 'signup' }) {
  const [mode, setMode] = useState(defaultMode); // 'signup' | 'login'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const fn = mode === 'signup' ? signup : login;
      const result = await fn(email, password);
      localStorage.setItem('or_token', result.token);
      localStorage.setItem('or_email', result.email);
      localStorage.removeItem('or_anon_token'); // promote out of anonymous
      onSuccess(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-overlay" onClick={onClose}>
      <div className="auth-dialog" onClick={(e) => e.stopPropagation()}>
        <button className="auth-close" onClick={onClose}>×</button>
        <h2>{mode === 'signup' ? 'Sign up' : 'Log in'}</h2>
        <p className="auth-subtitle">
          {mode === 'signup'
            ? 'Email + password only — no verification required.'
            : 'Welcome back!'}
        </p>
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoFocus
          />
          <input
            type="password"
            placeholder="password (min 6 chars)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
          />
          {error && <div className="auth-error">{error}</div>}
          <button type="submit" disabled={loading}>
            {loading ? '...' : mode === 'signup' ? 'Sign up' : 'Log in'}
          </button>
        </form>
        <div className="auth-switch">
          {mode === 'signup' ? (
            <>Already have an account? <a onClick={() => setMode('login')}>Log in</a></>
          ) : (
            <>Don't have an account? <a onClick={() => setMode('signup')}>Sign up</a></>
          )}
        </div>
      </div>
    </div>
  );
}
