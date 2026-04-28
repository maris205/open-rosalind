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
      const result = await analyze(input, mode, followUpSession);
      setCurrentResult(result);
      setFollowUpSession(result.session_id); // next query can follow up
      await loadSessions(); // refresh sidebar
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
        <h1>Open-Rosalind <span className="tag">MVP2</span></h1>
        <p>Local-first, tool-driven life-science research agent</p>
      </header>
      <div className="main-layout">
        <SessionSidebar
          sessions={sessions}
          onLoadSession={handleLoadSession}
          onRefresh={loadSessions}
        />
        <div className="content">
          <InputPanel onAnalyze={handleAnalyze} loading={loading} />
          {currentResult && <ResultPanel result={currentResult} />}
        </div>
      </div>
    </div>
  );
}
