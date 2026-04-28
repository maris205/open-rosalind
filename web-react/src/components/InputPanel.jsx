import { useState } from 'react';

export default function InputPanel({ onAnalyze, loading, execMode, setExecMode }) {
  const [input, setInput] = useState('');
  const [mode, setMode] = useState('auto');

  const demos = [
    'What is BRCA1 and where is it located?',
    'Find recent papers about CRISPR base editing',
    '>seq1\nMVKVGVNGFGRIGRLVTRA',
    'WT: MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGPDEAPRMPEAAPPVAPAPAAPTPAAPAPAPSWPLSSSVPSQKTYQGSYGFRLGFLHSGTAKSVTCTYSPALNKMFCQLAKTCPVQLWVDSTPPPGTRVRAMAIYKQSQHMTEVVRRCPHHERCSDSDGLAPPQHLIRVEGNLRVEYLDDRNTFRHSVVVPYEPPEVGSDCTTIHYNYMCNSSCMGGMNRRPILTIITLEDSSGNLLGRNSFEVRVCACPGRDRRTEEENLRKKGEPHHELPPGSTKRALPNNTSSSPQPKKKPLDGEYFTLQIRGRERFEMFRELNEALELKDAQAGKEPGGSRAHSSHLKSKKGQSTSRHKKLMFKTEGPDSD\nMT: p.R175H',
  ];

  return (
    <div className="panel input-panel">
      <div className="mode-switch">
        <label>
          <input type="radio" checked={execMode === 'single'} onChange={() => setExecMode('single')} />
          Single-step
        </label>
        <label>
          <input type="radio" checked={execMode === 'task'} onChange={() => setExecMode('task')} />
          Multi-step Task
        </label>
      </div>
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder={execMode === 'task' ? 'Describe your multi-step task (e.g., "Analyze this protein and find papers: MVKVGVNGFGRIGRLVTRA")' : 'Enter your question, sequence, or mutation...'}
        rows={6}
      />
      <div className="controls">
        <button onClick={() => onAnalyze(input, mode)} disabled={loading || !input.trim()}>
          {loading ? 'Running...' : execMode === 'task' ? 'Run Task' : 'Analyze'}
        </button>
        {execMode === 'single' && (
          <>
            <select value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="auto">Auto-detect</option>
              <option value="sequence">Sequence</option>
              <option value="mutation">Mutation</option>
            </select>
            <select onChange={(e) => setInput(e.target.value)} value="">
              <option value="">Demo prompts...</option>
              {demos.map((d, i) => (
                <option key={i} value={d}>{d.slice(0, 50)}</option>
              ))}
            </select>
          </>
        )}
      </div>
    </div>
  );
}
