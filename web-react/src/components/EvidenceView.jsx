function skillLabel(skill) {
  const map = {
    sequence_basic_analysis: 'Sequence analysis',
    uniprot_lookup: 'UniProt lookup',
    protein_annotation_summary: 'Protein annotation',
    literature_search: 'Literature search',
    mutation_effect: 'Mutation effect',
    workflow_protein_annotation: 'Protein annotation workflow',
    workflow_mutation_assessment: 'Mutation assessment workflow',
    protein_annotation: 'Protein annotation workflow',
    mutation_assessment: 'Mutation assessment workflow',
  };
  return map[skill] || skill || 'Evidence';
}

function formatValue(value) {
  if (value == null || value === '') return '—';
  if (Array.isArray(value)) return value.length ? value.join(', ') : '—';
  return String(value);
}

function compactText(value, max = 96) {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  if (!text) return '—';
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function summarizeObject(value) {
  if (!value || typeof value !== 'object') return formatValue(value);
  const keys = Object.keys(value);
  if (!keys.length) return '—';
  return `${keys.slice(0, 3).join(', ')}${keys.length > 3 ? '…' : ''}`;
}

function summarizeTracePayload(value, mode) {
  if (value == null) return '—';
  if (typeof value !== 'object') return compactText(value);
  if (Array.isArray(value)) return `${value.length} item(s)`;

  const parts = [];

  if (mode === 'input') {
    if (value.query) parts.push(`query=${compactText(value.query, 72)}`);
    if (value.accession) parts.push(`accession=${value.accession}`);
    if (value.mutation) parts.push(`mutation=${value.mutation}`);
    if (value.pmids?.length) parts.push(`pmids=${value.pmids.slice(0, 3).join(', ')}`);
    if (value.sequence) parts.push(`sequence(${String(value.sequence).length})`);
    if (value.wild_type) parts.push(`wild_type(${String(value.wild_type).length})`);
    if (value.mutant) parts.push(`mutant(${String(value.mutant).length})`);
    if (value.max_results != null) parts.push(`max=${value.max_results}`);
  } else {
    const errorMessage = value.error?.message || value.error;
    if (errorMessage) return compactText(errorMessage, 88);
    if (value.accession) parts.push(value.accession);
    if (value.name) parts.push(compactText(value.name, 42));
    if (value.count != null) parts.push(`${value.count} hit(s)`);
    if (value.hits?.length) parts.push(`${value.hits.length} hit(s) returned`);
    if (value.records?.length) parts.push(`${value.records.length} record(s)`);
    if (value.n_records != null) parts.push(`${value.n_records} record(s)`);
    if (value.n_differences != null) parts.push(`${value.n_differences} difference(s)`);
    if (value.overall_assessment) parts.push(value.overall_assessment);
    if (value.identity != null) parts.push(`identity ${(value.identity * 100).toFixed(0)}%`);
  }

  return parts.join(' · ') || summarizeObject(value);
}

function KeyValueTable({ rows }) {
  if (!rows.length) return null;
  return (
    <div className="kv">
      {rows.map(([key, value], index) => (
        <div key={index} className="kv-row">
          <div className="k">{key}</div>
          <div className="v">{formatValue(value)}</div>
        </div>
      ))}
    </div>
  );
}

function EvidenceNotes({ notes }) {
  if (!notes || notes.length === 0) return null;
  return (
    <div className="evidence-notes">
      {notes.map((note, index) => (
        <div key={index} className="note">{note}</div>
      ))}
    </div>
  );
}

function WorkflowSubsteps({ steps }) {
  if (!steps || steps.length === 0) return null;
  return (
    <div className="evidence-substeps">
      {steps.map((item, index) => (
        <div key={`${item.step || 'step'}-${index}`} className="evidence-substep">
          <div className="evidence-substep-title">{skillLabel(item.step)}</div>
          <EvidenceView evidence={item.result || {}} skill={item.step} />
        </div>
      ))}
    </div>
  );
}

function renderSequenceEvidence(evidence) {
  const record = evidence.sequence_stats?.records?.[0];
  const rows = [];
  if (record) {
    rows.push(['Type', record.type]);
    rows.push(['Length', `${record.length} ${record.type === 'protein' ? 'aa' : 'nt'}`]);
    if (record.molecular_weight != null) rows.push(['Molecular weight', `${record.molecular_weight.toFixed(1)} kDa`]);
    if (record.gc_percent != null) rows.push(['GC content', `${record.gc_percent.toFixed(1)}%`]);
    if (record.translation_preview) rows.push(['Translation', compactText(record.translation_preview, 48)]);
    if (record.reverse_complement_preview) rows.push(['Reverse complement', compactText(record.reverse_complement_preview, 48)]);
  }
  if (evidence.uniprot_hint?.top_match) rows.push(['Top UniProt match', evidence.uniprot_hint.top_match]);
  if (evidence.uniprot_hint?.hits) rows.push(['UniProt homology', `${evidence.uniprot_hint.hits} hit(s)`]);
  return (
    <>
      <KeyValueTable rows={rows} />
      <EvidenceNotes notes={evidence.notes} />
    </>
  );
}

function renderProteinEvidence(evidence) {
  const entry = evidence.entry || {};
  const search = evidence.search || {};
  const rows = [];
  if (entry.accession) rows.push(['Accession', entry.accession]);
  if (entry.name) rows.push(['Name', entry.name]);
  if (entry.organism) rows.push(['Organism', entry.organism]);
  if (entry.length != null) rows.push(['Length', `${entry.length} aa`]);
  if (entry.function) rows.push(['Function', compactText(entry.function, 180)]);
  if (search.count != null) rows.push(['Search hits', search.count]);
  const topHit = search.hits?.[0];
  if (topHit?.accession && topHit.accession !== entry.accession) rows.push(['Top search hit', topHit.accession]);
  return (
    <>
      <KeyValueTable rows={rows} />
      <EvidenceNotes notes={evidence.notes} />
    </>
  );
}

function renderLiteratureEvidence(evidence) {
  const pubmed = evidence.pubmed || {};
  const metadata = evidence.metadata?.records || [];
  const abstracts = evidence.abstracts?.records || [];
  const rows = [];
  if (pubmed.query) rows.push(['Query', compactText(pubmed.query, 140)]);
  if (pubmed.count != null) rows.push(['Hits', pubmed.count]);
  if (pubmed.hits?.length) {
    pubmed.hits.slice(0, 3).forEach((hit, index) => {
      rows.push([`PMID ${index + 1}`, `${hit.pmid}: ${compactText(hit.title, 88)}`]);
    });
  }
  if (metadata.length) rows.push(['Metadata fetched', metadata.length]);
  if (abstracts.length) rows.push(['Abstracts fetched', abstracts.length]);
  return (
    <>
      <KeyValueTable rows={rows} />
      <EvidenceNotes notes={evidence.notes} />
    </>
  );
}

function renderMutationEvidence(evidence) {
  const mutation = evidence.mutation || {};
  const context = evidence.protein_context || {};
  const rows = [];
  if (context.gene_symbol) rows.push(['Gene symbol', context.gene_symbol]);
  if (context.accession) rows.push(['Accession', context.accession]);
  if (context.name) rows.push(['Protein', context.name]);
  if (mutation.n_differences != null) rows.push(['Differences', mutation.n_differences]);
  if (mutation.overall_assessment) rows.push(['Assessment', mutation.overall_assessment]);
  if (mutation.differences?.length) {
    mutation.differences.slice(0, 4).forEach((difference) => {
      rows.push([
        `Position ${difference.position}`,
        `${difference.wt} → ${difference.mt} (${difference.severity})`,
      ]);
    });
  }
  return (
    <>
      <KeyValueTable rows={rows} />
      <EvidenceNotes notes={evidence.notes} />
    </>
  );
}

function renderWorkflowEvidence(evidence, skill) {
  const annotation = evidence.annotation || {};
  const rows = [];
  if (skill === 'workflow_protein_annotation' || annotation.workflow === 'protein_annotation') {
    if (annotation.primary_type) rows.push(['Primary type', annotation.primary_type]);
    if (annotation.length != null) rows.push(['Length', `${annotation.length} aa`]);
    if (annotation.accession) rows.push(['Accession', annotation.accession]);
    if (annotation.name) rows.push(['Protein', annotation.name]);
    if (annotation.organism) rows.push(['Organism', annotation.organism]);
  } else {
    if (annotation.gene_symbol) rows.push(['Gene symbol', annotation.gene_symbol]);
    if (annotation.accession) rows.push(['Accession', annotation.accession]);
    if (annotation.protein_name) rows.push(['Protein', annotation.protein_name]);
    if (annotation.organism) rows.push(['Organism', annotation.organism]);
    if (annotation.mutation) rows.push(['Mutation', annotation.mutation]);
    if (annotation.n_differences != null) rows.push(['Differences', annotation.n_differences]);
    if (annotation.overall_assessment) rows.push(['Assessment', annotation.overall_assessment]);
    if (annotation.literature_hits != null) rows.push(['Literature hits', annotation.literature_hits]);
  }

  return (
    <>
      <KeyValueTable rows={rows} />
      <EvidenceNotes notes={evidence.notes} />
      <WorkflowSubsteps steps={evidence.evidence} />
    </>
  );
}

function renderFallbackEvidence(evidence) {
  const annotation = evidence.annotation || {};
  const rows = Object.entries(annotation)
    .filter(([key]) => key !== 'kind' && key !== 'workflow')
    .map(([key, value]) => [key.replace(/_/g, ' '), Array.isArray(value) ? value.join(', ') : value]);
  return (
    <>
      <KeyValueTable rows={rows} />
      <EvidenceNotes notes={evidence.notes} />
    </>
  );
}

function inferEvidenceKind(skill, evidence) {
  const workflow = evidence?.annotation?.workflow;
  if (workflow === 'protein_annotation') return 'workflow_protein_annotation';
  if (workflow === 'mutation_assessment') return 'workflow_mutation_assessment';
  if (skill === 'protein_annotation') return 'workflow_protein_annotation';
  if (skill === 'mutation_assessment') return 'workflow_mutation_assessment';
  if (skill === 'protein_annotation_summary') return 'protein_annotation_summary';
  return skill || evidence?.annotation?.kind || '';
}

export function EvidenceView({ evidence, skill }) {
  if (!evidence || Object.keys(evidence).length === 0) {
    return <div className="evidence-empty">No structured evidence available</div>;
  }

  const kind = inferEvidenceKind(skill, evidence);

  if (kind === 'sequence_basic_analysis') return renderSequenceEvidence(evidence);
  if (kind === 'uniprot_lookup' || kind === 'protein_annotation_summary' || kind === 'protein') {
    return renderProteinEvidence(evidence);
  }
  if (kind === 'literature_search' || kind === 'literature') return renderLiteratureEvidence(evidence);
  if (kind === 'mutation_effect' || kind === 'mutation') return renderMutationEvidence(evidence);
  if (kind === 'workflow_protein_annotation' || kind === 'workflow_mutation_assessment') {
    return renderWorkflowEvidence(evidence, kind);
  }
  if (Array.isArray(evidence.evidence) && evidence.evidence.length) {
    return renderWorkflowEvidence(evidence, kind);
  }
  return renderFallbackEvidence(evidence);
}

export function TraceView({ trace }) {
  if (!trace || trace.length === 0) {
    return <div className="evidence-empty">No trace captured</div>;
  }

  return (
    <div className="trace-stack">
      {trace.map((step, index) => (
        <div key={index} className="trace-card">
          <div className="trace-card-header">
            <code>{step.tool || step.skill || `trace.${index + 1}`}</code>
            {step.status && (
              <span className={`trace-status-badge status-${step.status}`}>{step.status}</span>
            )}
            {step.latency_ms != null && <span className="trace-meta">{step.latency_ms}ms</span>}
          </div>
          <div className="trace-io">
            <span className="trace-io-label">in</span>
            <span>{summarizeTracePayload(step.input, 'input')}</span>
          </div>
          <div className="trace-io">
            <span className="trace-io-label">out</span>
            <span>{summarizeTracePayload(step.output, 'output')}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
