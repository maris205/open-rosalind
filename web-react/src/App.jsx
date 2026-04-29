import { useState, useEffect } from 'react';
import SessionSidebar from './components/SessionSidebar';
import InputPanel from './components/InputPanel';
import ResultPanel from './components/ResultPanel';
import { analyze, listSessions, getSession } from './api';
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

  async function handleLoadSession(session) {
    try {
      const data = await getSession(session.session_id);
      const events = data.events || [];

      // Extract relevant fields from event stream
      const startEv = events.find((e) => e.kind === 'start');
      const skillCallEv = events.find((e) => e.kind === 'skill_call');
      const skillResultEv = events.find((e) => e.kind === 'skill_result');
      const summaryEv = events.find((e) => e.kind === 'summary');

      const evidence = skillResultEv?.evidence || {};
      const annotation = skillResultEv?.annotation || null;
      const confidence = skillResultEv?.confidence ?? null;
      const notes = skillResultEv?.notes || [];

      // Reconstruct trace_steps from skill_call + skill_result
      const trace_steps = [];
      if (skillCallEv) {
        trace_steps.push({
          skill: skillCallEv.skill,
          input: skillCallEv.payload || {},
          output: skillResultEv?.evidence || {},
          status: skillResultEv ? 'success' : 'pending',
          latency_ms: null,
        });
      }

      setCurrentResult({
        exec_mode: 'single',
        session_id: session.session_id,
        skill: skillCallEv?.skill || 'unknown',
        summary: summaryEv?.text || `(No summary recorded for this session)`,
        annotation,
        confidence,
        notes,
        evidence,
        trace_steps,
      });
      setFollowUpSession(session.session_id);
    } catch (err) {
      alert(`Failed to load session: ${err.message}`);
    }
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
