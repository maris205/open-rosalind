import { useEffect, useRef, useState } from 'react';
import { EvidenceView, TraceView } from './EvidenceView';

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

function workflowToLabel(workflow) {
  const map = {
    workflow_protein_annotation: 'Protein annotation workflow',
    workflow_mutation_assessment: 'Mutation assessment workflow',
    protein_annotation: 'Protein annotation',
    mutation_assessment: 'Mutation assessment',
    sequence_basic_analysis: 'Sequence analysis',
    uniprot_lookup: 'UniProt lookup',
    literature_search: 'Literature search',
    mutation_effect: 'Mutation effect',
  };
  return map[workflow] || workflow;
}

function StepDetails({ step }) {
  const [showEvidence, setShowEvidence] = useState(false);
  const [showTrace, setShowTrace] = useState(false);
  const hasEvidence = step.evidence && Object.keys(step.evidence).length > 0;
  const hasTrace = step.trace && step.trace.length > 0;

  return (
    <div className="task-step-details">
      {step.summary && (
        <div className="task-step-summary markdown" dangerouslySetInnerHTML={{ __html: renderMarkdown(step.summary) }} />
      )}

      {step.error && (
        <div className="task-step-error">Error: {step.error}</div>
      )}

      <div className="task-step-meta">
        {step.latency_ms != null && (
          <span className="task-step-meta-chip">{step.latency_ms}ms</span>
        )}
        {hasEvidence && (
          <button className="step-toggle" onClick={() => setShowEvidence(!showEvidence)}>
            {showEvidence ? '▼' : '▶'} Evidence
          </button>
        )}
        {hasTrace && (
          <button className="step-toggle" onClick={() => setShowTrace(!showTrace)}>
            {showTrace ? '▼' : '▶'} Trace ({step.trace.length})
          </button>
        )}
      </div>

      {showEvidence && hasEvidence && (
        <div className="task-step-panel">
          <EvidenceView evidence={step.evidence} skill={step.executed_workflow || step.expected_workflow} />
        </div>
      )}

      {showTrace && hasTrace && (
        <div className="task-step-panel">
          <TraceView trace={step.trace} />
        </div>
      )}
    </div>
  );
}

function MessageEvidenceSection({ message }) {
  if (!message.evidence || Object.keys(message.evidence).length === 0) return null;

  if (message.execution_mode === 'harness' && message.steps?.length) {
    const stepMap = new Map(message.steps.map((step, index) => [step.step_id, { ...step, index }]));

    return (
      <div className="evidence-substeps">
        {Object.entries(message.evidence).map(([stepId, evidence]) => {
          const step = stepMap.get(stepId);
          const workflow = step?.executed_workflow || step?.expected_workflow;
          const workflowLabel = workflow ? workflowToLabel(workflow) : null;
          return (
            <div key={stepId} className="evidence-substep">
              <div className="evidence-substep-title">
                Step {step ? step.index + 1 : stepId}
                {workflowLabel ? ` · ${workflowLabel}` : ''}
              </div>
              {step?.instruction && <div className="evidence-substep-caption">{step.instruction}</div>}
              <EvidenceView evidence={evidence} skill={workflow || stepId} />
            </div>
          );
        })}
      </div>
    );
  }

  return <EvidenceView evidence={message.evidence} skill={message.skill} />;
}

function MessageTraceSection({ message }) {
  if (message.execution_mode === 'harness' && message.steps?.length) {
    const stepsWithTrace = message.steps.filter((step) => step.trace && step.trace.length > 0);
    if (!stepsWithTrace.length) return <div className="evidence-empty">No trace captured</div>;

    return (
      <div className="evidence-substeps">
        {stepsWithTrace.map((step, index) => {
          const workflow = step.executed_workflow || step.expected_workflow;
          const workflowLabel = workflow ? workflowToLabel(workflow) : null;
          return (
            <div key={step.step_id || index} className="evidence-substep">
              <div className="evidence-substep-title">
                Step {index + 1}
                {workflowLabel ? ` · ${workflowLabel}` : ''}
              </div>
              {step.instruction && <div className="evidence-substep-caption">{step.instruction}</div>}
              <TraceView trace={step.trace} />
            </div>
          );
        })}
      </div>
    );
  }

  return <TraceView trace={message.trace_steps} />;
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
  const traceCount = message.execution_mode === 'harness' && message.steps?.length
    ? message.steps.filter((step) => step.trace && step.trace.length > 0).length
    : (message.trace_steps?.length || 0);

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
                  <div className="step-row">
                    <span className={`step-status step-${s.status}`}>{s.status === 'success' ? '✓' : '✗'}</span>
                    <span className="step-text">{s.instruction}</span>
                  </div>
                  {(s.expected_workflow || s.executed_workflow) && (
                    <div className="step-workflows">
                      {s.expected_workflow && (
                        <span className="step-badge step-badge-expected">
                          expected: {workflowToLabel(s.expected_workflow)}
                        </span>
                      )}
                      {s.executed_workflow && (
                        <span className="step-badge step-badge-executed">
                          executed: {workflowToLabel(s.executed_workflow)}
                        </span>
                      )}
                    </div>
                  )}
                  <StepDetails step={s} />
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
            {showEvidence && (
              <div className="card-evidence">
                <MessageEvidenceSection message={message} />
              </div>
            )}
          </div>
        )}

        {traceCount > 0 && (
          <div className="card-section">
            <button className="card-toggle" onClick={() => setShowTrace(!showTrace)}>
              {showTrace ? '▼' : '▶'} Trace ({traceCount} {message.execution_mode === 'harness' ? 'task steps' : 'steps'})
            </button>
            {showTrace && (
              <div className="card-evidence">
                <MessageTraceSection message={message} />
              </div>
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
