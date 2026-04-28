import { useState } from 'react';

const DEMOS = [
  { label: 'BRCA1 lookup', input: 'What is BRCA1 and where is it located in the cell?', mode: 'uniprot' },
  { label: 'CRISPR papers', input: 'Find recent papers about CRISPR base editing in 2024', mode: 'literature' },
  { label: 'Protein sequence', input: '>demo\nMVKVGVNGFGRIGRLVTRAAFNSGKVDIVAINDPFIDLNYMVYMFQYDSTHGKFHGTVKAENGKLVINGNPITIF', mode: 'sequence' },
  { label: 'p53 R175H mutation', input: 'WT: MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGPDEAPRMPEAAPPVAPAPAAPTPAAPAPAPSWPLSSSVPSQKTYQGSYGFRLGFLHSGTAKSVTCTYSPALNKMFCQLAKTCPVQLWVDSTPPPGTRVRAMAIYKQSQHMTEVVRRCPHHERCSDSDGLAPPQHLIRVEGNLRVEYLDDRNTFRHSVVVPYEPPEVGSDCTTIHYNYMCNSSCMGGMNRRPILTIITLEDSSGNLLGRNSFEVRVCACPGRDRRTEEENLRKKGEPHHELPPGSTKRALPNNTSSSPQPKKKPLDGEYFTLQIRGRERFEMFRELNEALELKDAQAGKEPGGSRAHSSHLKSKKGQSTSRHKKLMFKTEGPDSD\nMT: p.R175H', mode: 'mutation' },
];

export default function InputPanel({ onAnalyze, loading }) {
  const [input, setInput] = useState('');
  const [mode, setMode] = useState('auto');

  function handleSubmit(e) {
    e.preventDefault();
    if (!input.trim() || loading) return;
    onAnalyze(input, mode);
  }

  function loadDemo(demo) {
    setInput(demo.input);
    setMode(demo.mode);
  }

  return (
    <div className="panel input-panel">
      <form onSubmit={handleSubmit}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Question / Sequence / UniProt accession"
          rows={6}
          disabled={loading}
        />
        <div className="controls">
          <button type="submit" disabled={loading || !input.trim()}>
            {loading ? 'Analyzing...' : 'Analyze'}
          </button>
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="auto">mode: auto</option>
            <option value="sequence">sequence</option>
            <option value="uniprot">uniprot</option>
            <option value="literature">literature</option>
            <option value="mutation">mutation</option>
          </select>
          <select onChange={(e) => { if (e.target.value) loadDemo(JSON.parse(e.target.value)); e.target.value = ''; }}>
            <option value="">— demo prompts —</option>
            {DEMOS.map((d, i) => (
              <option key={i} value={JSON.stringify(d)}>{d.label}</option>
            ))}
          </select>
        </div>
      </form>
    </div>
  );
}
