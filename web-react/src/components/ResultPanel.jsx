import { useState } from 'react';
import { EvidenceView, TraceView } from './EvidenceView';

export default function ResultPanel({ result }) {
  const [showTrace, setShowTrace] = useState(false);
  const [showRawEvidence, setShowRawEvidence] = useState(false);

  // Task mode
  if (result.exec_mode === 'task') {
    return (
      <div className="panel result-panel">
        <div className="card">
          <h2>Task: {result.task_id}</h2>
          <p>Status: <strong>{result.status}</strong></p>
          {result.warnings && result.warnings.length > 0 && (
            <div className="notes">
              <ul>{result.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
            </div>
          )}
        </div>
        <div className="card">
          <h2>Steps ({result.steps.length})</h2>
          <ol className="trace-list">
            {result.steps.map((s, i) => (
              <li key={i}>
                <span className="trace-skill">{s.status === 'success' ? '✅' : '❌'} {s.step_id}</span>
                <div>{s.instruction}</div>
                {s.summary && <div className="markdown" dangerouslySetInnerHTML={{ __html: renderMarkdown(s.summary.slice(0, 200)) }} />}
              </li>
            ))}
          </ol>
        </div>
        {result.final_report && (
          <div className="card">
            <h2>Final Report</h2>
            <div className="markdown" dangerouslySetInnerHTML={{ __html: renderMarkdown(result.final_report) }} />
          </div>
        )}
      </div>
    );
  }

  // Single-step mode
  const { session_id, skill, summary, annotation, confidence, notes, evidence, trace_steps } = result;

  return (
    <div className="panel result-panel">
      <div className="card">
        <h2>
          Summary
          <span className="meta">
            · skill: {skill} · session: {session_id?.slice(0, 19)}
          </span>
        </h2>
        {confidence != null && (
          <div className="confidence-row">
            <span className="conf-label">confidence</span>
            <div className="conf-bar">
              <div className="conf-fill" style={{ width: `${confidence * 100}%` }} />
            </div>
            <span className="conf-value">{confidence.toFixed(2)}</span>
          </div>
        )}
        {notes && notes.length > 0 && (
          <div className="notes">
            <ul>
              {notes.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          </div>
        )}
        <div className="markdown" dangerouslySetInnerHTML={{ __html: renderMarkdown(summary) }} />
      </div>

      {annotation && annotation.kind && annotation.kind !== 'unknown' && (
        <div className="card">
          <h2>Annotation</h2>
          <div className="annotation">{renderAnnotation(annotation)}</div>
        </div>
      )}

      <div className="card">
        <h2>
          Evidence
          <button className="btn-toggle" onClick={() => setShowRawEvidence(!showRawEvidence)}>
            {showRawEvidence ? 'Show human-readable' : 'Show raw JSON'}
          </button>
        </h2>
        {showRawEvidence ? (
          <pre>{JSON.stringify(evidence, null, 2)}</pre>
        ) : (
          <div className="evidence-human"><EvidenceView evidence={evidence} skill={skill} /></div>
        )}
      </div>

      {trace_steps && trace_steps.length > 0 && (
        <div className="card">
          <h2>
            Trace
            <button className="btn-toggle" onClick={() => setShowTrace(!showTrace)}>
              {showTrace ? 'Hide' : 'Show'}
            </button>
          </h2>
          {showTrace && <TraceView trace={trace_steps} />}
        </div>
      )}
    </div>
  );
}

function renderMarkdown(md) {
  if (!md) return '';
  return md
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/^### (.*)$/gm, '<h3>$1</h3>')
    .replace(/^## (.*)$/gm, '<h2>$1</h2>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n/g, '<br/>');
}

function renderAnnotation(ann) {
  const rows = [];
  if (ann.kind === 'protein') {
    rows.push(['Name', ann.name]);
    rows.push(['Accession', ann.accession]);
    rows.push(['Organism', ann.organism]);
    rows.push(['Length', ann.length]);
    rows.push(['Function', ann.function]);
  } else if (ann.kind === 'literature') {
    rows.push(['Hits', ann.n_hits]);
    rows.push(['Query', ann.query_used]);
    rows.push(['PMIDs', (ann.top_pmids || []).join(', ')]);
  } else if (ann.kind === 'mutation') {
    rows.push(['Differences', ann.n_differences]);
    rows.push(['Assessment', ann.overall_assessment]);
    rows.push(['Flags', (ann.notable_flags || []).join(' · ')]);
  }
  return (
    <div className="kv">
      {rows.map(([k, v], i) => (
        <div key={i} className="kv-row">
          <div className="k">{k}</div>
          <div className="v">{v || '—'}</div>
        </div>
      ))}
    </div>
  );
}
