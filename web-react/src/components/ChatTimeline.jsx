import { useEffect, useRef, useState } from 'react';

function escapeHtml(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Convert numeric confidence (0..1) to a human-readable label
function confidenceLabel(c) {
  const v = c.toFixed(2);
  if (c >= 0.85) return `High (${v})`;
  if (c >= 0.6) return `Medium (${v})`;
  if (c >= 0.3) return `Low (${v})`;
  return `Very low (${v})`;
}

// Map internal skill name → user-facing source label
function skillToSource(skill) {
  const map = {
    sequence_basic_analysis: 'Sequence (BioPython)',
    uniprot_lookup: 'UniProt',
    literature_search: 'PubMed',
    mutation_effect: 'Mutation diff',
  };
  return map[skill] || skill;
}

function renderMarkdown(md) {
  if (!md) return '';
  return escapeHtml(md)
    .replace(/^### (.*)$/gm, '<h3>$1</h3>')
    .replace(/^## (.*)$/gm, '<h2>$1</h2>')
    .replace(/^# (.*)$/gm, '<h2>$1</h2>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n/g, '<br/>');
}

function AssistantCard({ message, onSignupClick }) {
  const [showTrace, setShowTrace] = useState(false);
  const [showEvidence, setShowEvidence] = useState(false);

  // Special card: requires_signup
  if (message.requires_signup) {
    return (
      <div className="msg msg-assistant">
        <div className="card-signup">
          <div className="signup-icon">🔒</div>
          <h3>Sign up to continue</h3>
          <p>Anonymous users can have one conversation. To start a new session, please sign up.</p>
          <p className="signup-hint">Email + password only — no email verification required.</p>
          <button className="btn-primary" onClick={onSignupClick}>Sign up</button>
        </div>
      </div>
    );
  }

  return (
    <div className="msg msg-assistant">
      <div className="card-result">
        <div className="card-header">
          <span className="exec-mode-badge" data-mode={message.execution_mode}>
            {message.execution_mode === 'harness' ? '🔗 Multi-step research' : '⚡ Quick analysis'}
          </span>
          {message.confidence != null && (
            <span className="confidence-badge" title={`Score: ${message.confidence.toFixed(2)}`}>
              🧬 Confidence: {confidenceLabel(message.confidence)}
            </span>
          )}
          {message.skill && message.skill !== 'harness' && (
            <span className="skill-badge" title={`Skill: ${message.skill}`}>
              🔬 Source: {skillToSource(message.skill)}
            </span>
          )}
        </div>

        <div className="card-summary markdown" dangerouslySetInnerHTML={{ __html: renderMarkdown(message.summary) }} />

        {message.notes && message.notes.length > 0 && (
          <div className="card-notes">
            {message.notes.map((n, i) => <div key={i} className="note">⚠ {n}</div>)}
          </div>
        )}

        {message.steps && message.steps.length > 0 && (
          <div className="card-steps">
            <div className="card-section-label">Steps</div>
            <ol>
              {message.steps.map((s, i) => (
                <li key={i}>
                  <span className={`step-status step-${s.status}`}>{s.status === 'success' ? '✓' : '✗'}</span>
                  {' '}{s.instruction}
                </li>
              ))}
            </ol>
          </div>
        )}

        {message.evidence && Object.keys(message.evidence).length > 0 && (
          <div className="card-section">
            <button className="card-toggle" onClick={() => setShowEvidence(!showEvidence)}>
              {showEvidence ? '▼' : '▶'} Evidence
            </button>
            {showEvidence && <pre className="card-pre">{JSON.stringify(message.evidence, null, 2)}</pre>}
          </div>
        )}

        {message.trace_steps && message.trace_steps.length > 0 && (
          <div className="card-section">
            <button className="card-toggle" onClick={() => setShowTrace(!showTrace)}>
              {showTrace ? '▼' : '▶'} Trace ({message.trace_steps.length} steps)
            </button>
            {showTrace && (
              <ol className="card-trace">
                {message.trace_steps.map((s, i) => (
                  <li key={i}>
                    <code>{s.skill}</code>
                    {s.latency_ms != null && <span className="trace-meta"> · {s.latency_ms}ms</span>}
                    <span className={`trace-status status-${s.status}`}> · {s.status}</span>
                  </li>
                ))}
              </ol>
            )}
          </div>
        )}

        <div className="card-meta">
          <span title={message.execution_reason}>{message.execution_reason}</span>
        </div>
      </div>
    </div>
  );
}

export default function ChatTimeline({ messages, loading, onSignupClick }) {
  const ref = useRef(null);

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [messages, loading]);

  if (messages.length === 0 && !loading) {
    return (
      <div className="chat-empty">
        <div className="empty-icon">🧬</div>
        <h2>Ask biology. Get answers you can trust.</h2>
        <p className="empty-tagline">A tool-driven bio-agent for reproducible life science research.</p>
        <div className="suggestions">
          <div className="suggestion">"What is BRCA1?"</div>
          <div className="suggestion">"Find papers about CRISPR base editing"</div>
          <div className="suggestion">"Analyze sequence MVKVGVNGFGRIGRLVTRA and find similar proteins"</div>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-timeline" ref={ref}>
      {messages.map((m, i) => (
        m.role === 'user' ? (
          <div key={i} className="msg msg-user"><div className="msg-bubble">{m.content}</div></div>
        ) : (
          <AssistantCard key={i} message={m} onSignupClick={onSignupClick} />
        )
      ))}
      {loading && (
        <div className="msg msg-assistant">
          <div className="card-result">
            <div className="loading-dots"><span></span><span></span><span></span></div>
          </div>
        </div>
      )}
    </div>
  );
}
