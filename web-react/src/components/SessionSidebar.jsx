import { useState } from 'react';

export default function SessionSidebar({ sessions, onLoadSession, onRefresh }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h3>Sessions</h3>
        <button onClick={onRefresh} className="btn-icon" title="Refresh">↻</button>
      </div>
      <ul className="session-list">
        {sessions.map((s) => (
          <li key={s.session_id} onClick={() => onLoadSession(s)} className="session-item">
            <div className="session-input">{s.user_input?.slice(0, 60) || '(empty)'}</div>
            <div className="session-meta">{s.session_id.slice(0, 19)}</div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
