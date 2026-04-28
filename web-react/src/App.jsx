import { useState, useEffect } from 'react';
import SessionSidebar from './components/SessionSidebar';
import InputPanel from './components/InputPanel';
import ResultPanel from './components/ResultPanel';
import { analyze, listSessions } from './api';
import './App.css';

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [currentResult, setCurrentResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [followUpSession, setFollowUpSession] = useState(null);
  const [execMode, setExecMode] = useState('single'); // 'single' | 'task'

  useEffect(() => {
    loadSessions();
  }, []);

  async function loadSessions() {
    try {
      const data = await listSessions();
      setSessions(data.sessions || []);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  }

  async function handleAnalyze(input, mode) {
    setLoading(true);
    try {
      if (execMode === 'task') {
        // Multi-step task mode
        const res = await fetch('/api/task/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ goal: input, max_steps: 5 }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const result = await res.json();
        setCurrentResult({ ...result, exec_mode: 'task' });
      } else {
        // Single-step mode
        const result = await analyze(input, mode, followUpSession);
        setCurrentResult({ ...result, exec_mode: 'single' });
        setFollowUpSession(result.session_id);
        await loadSessions();
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function handleLoadSession(session) {
    // For now, just show the session_id and user_input in the result panel
    // A full implementation would replay the session events
    setCurrentResult({
      session_id: session.session_id,
      summary: `Session loaded: ${session.user_input}\n\n(Full session replay coming soon)`,
      evidence: {},
      trace_steps: [],
    });
    setFollowUpSession(session.session_id);
  }

  return (
    <div className="app">
      <header>
        <h1>Open-Rosalind <span className="tag">MVP3</span></h1>
        <p>Local-first, tool-driven bioinformatics agent</p>
      </header>
      <div className="main-layout">
        <SessionSidebar
          sessions={sessions}
          onLoadSession={handleLoadSession}
          onRefresh={loadSessions}
        />
        <div className="content">
          <InputPanel onAnalyze={handleAnalyze} loading={loading} execMode={execMode} setExecMode={setExecMode} />
          {currentResult && <ResultPanel result={currentResult} />}
        </div>
      </div>
    </div>
  );
}
