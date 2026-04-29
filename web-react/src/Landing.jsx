import './Landing.css';

const GITHUB_URL = 'https://github.com/maris205/open-rosalind';

export default function Landing() {
  return (
    <div className="landing">
      {/* === Top nav === */}
      <nav className="landing-nav">
        <div className="nav-brand">
          <span className="nav-icon">🧬</span>
          <span className="nav-name">Open-Rosalind</span>
        </div>
        <div className="nav-links">
          <a href="#why">Why</a>
          <a href="#how">How it works</a>
          <a href="#principles">Principles</a>
          <a href={GITHUB_URL} target="_blank" rel="noreferrer">GitHub ↗</a>
          <a href="#/app" className="nav-cta">Launch App →</a>
        </div>
      </nav>

      {/* === Hero === */}
      <section className="hero">
        <div className="hero-text">
          <h1 className="hero-title">
            Ask biology.<br />
            <span className="hero-gradient">Get answers you can trust.</span>
          </h1>
          <p className="hero-subtitle">
            Open-Rosalind is a tool-driven bio-agent for reproducible life science research —
            with structured workflows, evidence grounding, and full traceability.
          </p>
          <div className="hero-cta">
            <a href="#/app" className="btn-primary-lg">Launch App →</a>
            <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="btn-secondary-lg">
              View on GitHub ↗
            </a>
          </div>
          <div className="hero-meta">
            <span>✓ Free to use</span>
            <span>✓ MIT open source</span>
            <span>✓ Works with any LLM</span>
          </div>
        </div>
        <div className="hero-visual">
          <div className="demo-card">
            <div className="demo-header">
              <span className="demo-dot dot-r"></span>
              <span className="demo-dot dot-y"></span>
              <span className="demo-dot dot-g"></span>
              <span className="demo-title">Open-Rosalind</span>
            </div>
            <div className="demo-body">
              <div className="demo-msg msg-user-demo">What is BRCA1?</div>
              <div className="demo-msg msg-ai">
                <div className="demo-badges">
                  <span className="badge badge-mode">⚡ Quick analysis</span>
                  <span className="badge badge-conf">🧬 Confidence: High (0.95)</span>
                  <span className="badge badge-src">🔬 UniProt</span>
                </div>
                <div className="demo-summary">
                  <strong>P38398</strong> is the Breast cancer type 1 susceptibility protein
                  in <em>Homo sapiens</em> <span className="cite">[UniProt:P38398]</span>. It functions
                  as an <strong>E3 ubiquitin-protein ligase</strong>, central to DNA repair...
                </div>
                <div className="demo-trace">
                  <code>uniprot.fetch</code> → <code>BRCA1_HUMAN</code> · 1561ms
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* === Why === */}
      <section id="why" className="section">
        <h2 className="section-title">Not another AI assistant.</h2>
        <p className="section-subtitle">A different way to do bioinformatics.</p>

        <div className="compare-grid">
          <div className="compare-card compare-bad">
            <div className="compare-icon">❌</div>
            <h3>General AI Agents</h3>
            <ul>
              <li>Free-form reasoning</li>
              <li>Optional tool usage</li>
              <li>Unstructured outputs</li>
              <li>Hard to reproduce</li>
              <li>Hallucinated PMIDs / accessions</li>
            </ul>
          </div>
          <div className="compare-card compare-good">
            <div className="compare-icon">✅</div>
            <h3>Open-Rosalind</h3>
            <ul>
              <li><strong>Tool-first execution</strong></li>
              <li>Structured workflows (MCP-style)</li>
              <li>Evidence-grounded results</li>
              <li>Full traceability</li>
              <li>Real UniProt + PubMed citations</li>
            </ul>
          </div>
        </div>
        <p className="section-tagline">
          Designed for scientific workflows, not casual answers.
        </p>
      </section>

      {/* === Demos === */}
      <section className="section section-alt">
        <h2 className="section-title">Three ways to use Open-Rosalind</h2>
        <div className="demo-grid">
          <div className="demo-tile">
            <div className="demo-tile-icon">🧬</div>
            <h3>Protein Analysis</h3>
            <p>Input a sequence → get annotation, evidence, and trace.</p>
            <pre className="demo-code">{`> Analyze MVKVGVNGFGRIGRLVTRA
type: protein, length: 19aa
similar to GAPDH [UniProt:P04406]`}</pre>
          </div>
          <div className="demo-tile">
            <div className="demo-tile-icon">📚</div>
            <h3>Literature Search</h3>
            <p>Find papers → structured summary with PMID citations.</p>
            <pre className="demo-code">{`> Find papers on CRISPR base editing 2024
5 hits [PMID:38308006, PMID:38786024, ...]`}</pre>
          </div>
          <div className="demo-tile">
            <div className="demo-tile-icon">🧪</div>
            <h3>Mutation Analysis</h3>
            <p>Compare WT vs mutant → impact assessment.</p>
            <pre className="demo-code">{`> WT: ATCG  MT: ATGG
1 difference: C→G, severity: moderate`}</pre>
          </div>
        </div>
      </section>

      {/* === How it works === */}
      <section id="how" className="section">
        <h2 className="section-title">How it works</h2>
        <p className="section-subtitle">
          Every result is generated through tools, structured workflows, and verifiable evidence.
        </p>
        <div className="flow">
          <div className="flow-step">
            <div className="flow-icon">💬</div>
            <div className="flow-label">User Query</div>
          </div>
          <div className="flow-arrow">↓</div>
          <div className="flow-step">
            <div className="flow-icon">🧠</div>
            <div className="flow-label">Router (rule + LLM-assisted)</div>
          </div>
          <div className="flow-arrow">↓</div>
          <div className="flow-step">
            <div className="flow-icon">⚙️</div>
            <div className="flow-label">Workflow (MCP-style, max 5 steps)</div>
          </div>
          <div className="flow-arrow">↓</div>
          <div className="flow-step">
            <div className="flow-icon">🔬</div>
            <div className="flow-label">Skills (UniProt · PubMed · BioPython · Mutation)</div>
          </div>
          <div className="flow-arrow">↓</div>
          <div className="flow-step">
            <div className="flow-icon">📋</div>
            <div className="flow-label">Evidence + Trace</div>
          </div>
          <div className="flow-arrow">↓</div>
          <div className="flow-step flow-step-final">
            <div className="flow-icon">✨</div>
            <div className="flow-label">Final Answer (with citations)</div>
          </div>
        </div>
      </section>

      {/* === Principles === */}
      <section id="principles" className="section section-alt">
        <h2 className="section-title">Built on four principles</h2>
        <div className="principles-grid">
          <div className="principle-card">
            <div className="principle-icon">🛠️</div>
            <h3>Tool-first</h3>
            <p>No hallucinated science — only tool-backed results.</p>
          </div>
          <div className="principle-card">
            <div className="principle-icon">🔍</div>
            <h3>Evidence-grounded</h3>
            <p>Every answer is supported by explicit evidence.</p>
          </div>
          <div className="principle-card">
            <div className="principle-icon">📜</div>
            <h3>Traceable</h3>
            <p>Every step is recorded and reproducible.</p>
          </div>
          <div className="principle-card">
            <div className="principle-icon">🧭</div>
            <h3>Workflow-constrained</h3>
            <p>Structured pipelines instead of free-form reasoning.</p>
          </div>
        </div>
      </section>

      {/* === Benchmark === */}
      <section className="section">
        <h2 className="section-title">Evaluated with BioBench</h2>
        <p className="section-subtitle">
          Open-Rosalind is evaluated on structured bio-agent tasks, measuring not only accuracy,
          but also tool correctness, evidence grounding, and trace completeness.
        </p>
        <div className="bench-grid">
          <div className="bench-card">
            <div className="bench-score">100%</div>
            <div className="bench-label">BioBench v0</div>
            <div className="bench-desc">basic skills · 32 tasks</div>
          </div>
          <div className="bench-card">
            <div className="bench-score">93.9%</div>
            <div className="bench-label">BioBench v1</div>
            <div className="bench-desc">workflow + edge cases · 49 tasks</div>
          </div>
          <div className="bench-card">
            <div className="bench-score">90%</div>
            <div className="bench-label">BioBench v0.3</div>
            <div className="bench-desc">multi-step harness · 10 tasks</div>
          </div>
        </div>
        <p className="bench-meta">
          Five metrics tracked per run: <strong>Task accuracy</strong> · <strong>Tool correctness</strong>{' '}
          · <strong>Evidence rate</strong> · <strong>Trace completeness</strong> · <strong>Failure rate</strong>.
        </p>
      </section>

      {/* === Open source / CTA === */}
      <section className="section section-cta">
        <h2 className="cta-title">Open-Rosalind is open source.</h2>
        <p className="cta-subtitle">
          Build your own bio-agent. Extend skills. Run locally.
        </p>
        <div className="cta-buttons">
          <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="btn-primary-lg">
            View on GitHub ↗
          </a>
          <a href="#/app" className="btn-secondary-lg">Launch App →</a>
        </div>
      </section>

      {/* === Footer === */}
      <footer className="landing-footer">
        <div className="footer-left">
          <span className="nav-icon">🧬</span> Open-Rosalind ·
          <a href={GITHUB_URL} target="_blank" rel="noreferrer">GitHub</a> ·
          <a href={`${GITHUB_URL}/blob/main/LICENSE`} target="_blank" rel="noreferrer">MIT</a>
        </div>
        <div className="footer-right">
          A tool-driven bio-agent for reproducible research.
        </div>
      </footer>
    </div>
  );
}
