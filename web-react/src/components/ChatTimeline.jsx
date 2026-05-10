import { useEffect, useRef, useState } from 'react';
import { EvidenceView, TraceView } from './EvidenceView';
import MarkdownContent, { extractLeadSummary } from './MarkdownContent';

function compactText(text, max = 220) {
  const clean = String(text || '').replace(/\s+/g, ' ').trim();
  if (!clean) return '';
  return clean.length > max ? `${clean.slice(0, max - 1)}…` : clean;
}

function buildHarnessSummary(message) {
  const steps = message.steps || [];
  const successful = steps.filter((step) => step.status === 'success').length;
  const stepSummaries = steps
    .map((step) => extractLeadSummary(step?.summary || '', 220))
    .filter(Boolean)
    .slice(0, 3);
  const lines = [
    `Task completed with ${successful}/${steps.length} successful step${steps.length === 1 ? '' : 's'}.`,
  ];
  if (stepSummaries.length) {
    lines.push(stepSummaries.join('\n\n'));
  }
  return lines.join('\n\n');
}

function normalizeMarkdownText(text) {
  let normalized = String(text || '').replace(/\r\n?/g, '\n').trim();
  if (normalized.includes('\\n') && !normalized.includes('\n')) {
    normalized = normalized.replace(/\\n/g, '\n').trim();
  }
  return normalized;
}

function splitMarkdownSections(markdown) {
  const text = normalizeMarkdownText(markdown);
  if (!text) return [];

  const headingRe = /^##\s+(.+?)\s*$/gm;
  const matches = [...text.matchAll(headingRe)];
  if (!matches.length) return [{ title: 'Summary', body: text }];

  const sections = [];
  const lead = text.slice(0, matches[0].index).trim();
  if (lead) sections.push({ title: 'Summary', body: lead });

  matches.forEach((match, index) => {
    const start = (match.index || 0) + match[0].length;
    const end = index + 1 < matches.length ? matches[index + 1].index || text.length : text.length;
    const body = text.slice(start, end).trim();
    if (body) sections.push({ title: match[1].trim(), body });
  });

  return sections;
}

function takeSection(sections, pattern) {
  const index = sections.findIndex((section) => pattern.test(section.title));
  if (index < 0) return null;
  const [section] = sections.splice(index, 1);
  return section;
}

function CollapsibleSection({ title, children, defaultOpen = false, meta = '' }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="collapse-section">
      <button className="collapse-toggle" onClick={() => setOpen(!open)}>
        <span>{open ? '▼' : '▶'} {title}</span>
        {meta && <span className="collapse-meta">{meta}</span>}
      </button>
      {open && <div className="collapse-body">{children}</div>}
    </div>
  );
}

function HarnessReport({ content }) {
  const sections = splitMarkdownSections(content);
  const remaining = [...sections];
  const summary = takeSection(remaining, /^summary$/i);
  const annotation = takeSection(remaining, /^annotation$/i);
  const evidence = takeSection(remaining, /^evidence\b/i);
  const workflowTrace = takeSection(remaining, /^workflow\s+trace$/i);
  const confidence = takeSection(remaining, /^confidence$/i);
  const warnings = takeSection(remaining, /^warnings?$/i);

  if (!sections.length) return null;

  return (
    <div className="harness-report">
      {summary && <MarkdownContent content={summary.body} className="card-summary harness-summary" />}
      {annotation && (
        <div className="harness-support">
          <div className="card-section-label">Annotation</div>
          <MarkdownContent content={annotation.body} className="harness-section-markdown" />
        </div>
      )}
      {warnings && (
        <CollapsibleSection title="Warnings" defaultOpen>
          <MarkdownContent content={warnings.body} className="harness-section-markdown" />
        </CollapsibleSection>
      )}
      {evidence && (
        <CollapsibleSection title={evidence.title}>
          <MarkdownContent content={evidence.body} className="harness-section-markdown" />
        </CollapsibleSection>
      )}
      {workflowTrace && (
        <CollapsibleSection title={workflowTrace.title}>
          <MarkdownContent content={workflowTrace.body} className="harness-section-markdown" />
        </CollapsibleSection>
      )}
      {confidence && (
        <CollapsibleSection title={confidence.title}>
          <MarkdownContent content={confidence.body} className="harness-section-markdown" />
        </CollapsibleSection>
      )}
      {remaining.map((section) => (
        <CollapsibleSection key={section.title} title={section.title}>
          <MarkdownContent content={section.body} className="harness-section-markdown" />
        </CollapsibleSection>
      ))}
    </div>
  );
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
    model_only: 'Model only',
    sequence_basic_analysis: 'Sequence (BioPython)',
    uniprot_lookup: 'UniProt',
    literature_search: 'PubMed',
    mutation_effect: 'Mutation diff',
  };
  return map[skill] || skill;
}

function workflowToLabel(workflow) {
  const map = {
    model_only: 'Model-only answer',
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
        <MarkdownContent content={step.summary} className="task-step-summary" />
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

function AssistantCard({ message, onSignupClick }) {
  const [showTrace, setShowTrace] = useState(false);
  const [showEvidence, setShowEvidence] = useState(false);
  const traceCount = message.execution_mode === 'harness' && message.steps?.length
    ? message.steps.filter((step) => step.trace && step.trace.length > 0).length
    : (message.trace_steps?.length || 0);
  const renderedSummary = message.execution_mode === 'harness'
    ? (message.final_report || message.summary || buildHarnessSummary(message))
    : message.summary;
  const modeLabel = message.execution_mode === 'harness'
    ? '🔗 Multi-step research'
    : message.execution_mode === 'model_only'
      ? '💬 Model answer'
      : '⚡ Quick analysis';

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
            {modeLabel}
          </span>
          {message.confidence != null && (
            <span className="confidence-badge" title={`Score: ${message.confidence.toFixed(2)}`}>
              🧬 Confidence: {confidenceLabel(message.confidence)}
            </span>
          )}
          {message.skill && message.skill !== 'harness' && (
            <span className="skill-badge" title={`Skill: ${message.skill}`}>
              {message.skill === 'model_only' ? '💬 Source: No external tools' : `🔬 Source: ${skillToSource(message.skill)}`}
            </span>
          )}
        </div>

        {message.execution_mode === 'harness'
          ? <HarnessReport content={renderedSummary} />
          : <MarkdownContent content={renderedSummary} className="card-summary" />}

        {message.notes && message.notes.length > 0 && (
          <div className="card-notes">
            {message.notes.map((n, i) => <div key={i} className="note">⚠ {n}</div>)}
          </div>
        )}

        {message.steps && message.steps.length > 0 && (
          <CollapsibleSection title="Steps" meta={`${message.steps.length} step${message.steps.length === 1 ? '' : 's'}`}>
            <div className="card-steps">
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
          </CollapsibleSection>
        )}

        {message.evidence && Object.keys(message.evidence).length > 0 && message.execution_mode !== 'harness' && (
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

        {traceCount > 0 && message.execution_mode !== 'harness' && (
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
