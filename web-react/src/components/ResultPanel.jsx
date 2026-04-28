import { useState } from 'react';

export default function ResultPanel({ result }) {
  const { session_id, skill, summary, annotation, confidence, notes, evidence, trace_steps } = result;
  const [showTrace, setShowTrace] = useState(false);
  const [showRawEvidence, setShowRawEvidence] = useState(false);

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
          <div className="evidence-human">{renderEvidenceHuman(evidence, skill)}</div>
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
          {showTrace && (
            <ol className="trace-list">
              {trace_steps.map((s, i) => (
                <li key={i}>
                  <span className="trace-skill">{s.skill}</span>
                  <span className="trace-io">
                    ← {JSON.stringify(s.input).slice(0, 80)} → {JSON.stringify(s.output).slice(0, 120)}
                  </span>
                </li>
              ))}
            </ol>
          )}
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

function renderEvidenceHuman(evidence, skill) {
  const rows = [];

  if (skill === 'sequence_basic_analysis' && evidence.sequence_stats) {
    const rec = evidence.sequence_stats.records?.[0];
    if (rec) {
      rows.push(['Type', rec.type]);
      rows.push(['Length', `${rec.length} ${rec.type === 'protein' ? 'aa' : 'nt'}`]);
      if (rec.molecular_weight) rows.push(['Molecular weight', `${rec.molecular_weight.toFixed(1)} kDa`]);
      if (rec.gc_percent != null) rows.push(['GC content', `${rec.gc_percent.toFixed(1)}%`]);
      if (rec.translation_preview) rows.push(['Translation', rec.translation_preview]);
      if (rec.reverse_complement_preview) rows.push(['Reverse complement', rec.reverse_complement_preview.slice(0, 60)]);
    }
    if (evidence.uniprot_hint?.hits?.length) {
      rows.push(['UniProt homology', `${evidence.uniprot_hint.hits.length} hit(s)`]);
    }
  } else if (skill === 'uniprot_lookup') {
    if (evidence.entry) {
      rows.push(['Accession', evidence.entry.accession]);
      rows.push(['Name', evidence.entry.name]);
      rows.push(['Organism', evidence.entry.organism]);
      rows.push(['Length', `${evidence.entry.length} aa`]);
      if (evidence.entry.function) rows.push(['Function', evidence.entry.function.slice(0, 200) + '...']);
    }
    if (evidence.search) {
      rows.push(['Search hits', evidence.search.count || 0]);
    }
  } else if (skill === 'literature_search' && evidence.pubmed) {
    rows.push(['Query', evidence.pubmed.query]);
    rows.push(['Hits', evidence.pubmed.count || 0]);
    if (evidence.pubmed.hits?.length) {
      rows.push(['Top papers', '']);
      evidence.pubmed.hits.slice(0, 3).forEach((h, i) => {
        rows.push([`  ${i + 1}. PMID:${h.pmid}`, h.title]);
      });
    }
  } else if (skill === 'mutation_effect' && evidence.mutation) {
    rows.push(['Differences', evidence.mutation.n_differences]);
    rows.push(['Assessment', evidence.mutation.overall_assessment]);
    if (evidence.mutation.differences?.length) {
      evidence.mutation.differences.forEach((d, i) => {
        rows.push([`Position ${d.position}`, `${d.wild_type} → ${d.mutant} (${d.severity})`]);
      });
    }
  }

  if (rows.length === 0) {
    return <div className="evidence-empty">No structured evidence available</div>;
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
