# Mini BioBench — mvp3-v1-check run

- Date: `2026-04-28T11:53:53+00:00`
- Backend model: `google/gemma-4-26b-a4b-it`
- Git SHA: `2a79fd7`
- Tasks: **49**

## Headline metrics

| Metric | Value |
|---|---|
| Task accuracy        | **93.9%** |
| Tool correctness     | **100.0%** |
| Evidence rate        | **100.0%** |
| Trace completeness   | **100.0%** |
| Failure rate         | **0.0%** |

## By category

| Category | n | Task acc | Tool ok | Evidence | Trace | Failure |
|---|---|---|---|---|---|---|
| sequence_basic | 8 | 100% | 100% | 100% | 100% | 0% |
| literature_search | 6 | 100% | 100% | 100% | 100% | 0% |
| protein_annotation | 6 | 100% | 100% | 100% | 100% | 0% |
| mutation_effect | 6 | 100% | 100% | 100% | 100% | 0% |
| protocol_reasoning | 6 | 100% | 100% | 100% | 100% | 0% |
| workflow | 6 | 83% | 100% | 100% | 100% | 0% |
| edge_case | 4 | 100% | 100% | 100% | 100% | 0% |
| follow_up | 4 | 50% | 100% | 100% | 100% | 0% |
| stress | 3 | 100% | 100% | 100% | 100% | 0% |

## Per-task detail

| ID | Category | Pass | Skill | Tool | KW | Check |
|---|---|---|---|---|---|---|
| `seq-01` | sequence_basic | ✅ | ✓ | ✓ | 2/2 | got='dna' expected='dna' |
| `seq-02` | sequence_basic | ✅ | ✓ | ✓ | 2/2 | got='protein' expected='protein' |
| `seq-03` | sequence_basic | ✅ | ✓ | ✓ | 1/1 | got=49 expected=49 |
| `seq-04` | sequence_basic | ✅ | ✓ | ✓ | 2/2 | got=71.43 approx=71.43 tol=0.5 |
| `seq-05` | sequence_basic | ✅ | ✓ | ✓ | 1/1 | got='MRT*' starts_with='MRT' |
| `seq-06` | sequence_basic | ✅ | ✓ | ✓ | 1/1 | got='TTACGTACGCAT' starts_with='TTACGT' |
| `seq-07` | sequence_basic | ✅ | ✓ | ✓ | 1/1 | got=1 expected=1 |
| `seq-08` | sequence_basic | ✅ | ✓ | ✓ | 2/2 | got='dna' expected='dna' |
| `lit-01` | literature_search | ✅ | ✓ | ✓ | 2/2 | got=5 min=1 |
| `lit-02` | literature_search | ✅ | ✓ | ✓ | 1/1 | got=5 min=1 |
| `lit-03` | literature_search | ✅ | ✓ | ✓ | 1/1 | got=5 min=1 |
| `lit-04` | literature_search | ✅ | ✓ | ✓ | 2/2 | got=5 min=1 |
| `lit-05` | literature_search | ✅ | ✓ | ✓ | 1/1 | got=5 min=1 |
| `lit-06` | literature_search | ✅ | ✓ | ✓ | 1/2 | got=5 min=1 |
| `ann-01` | protein_annotation | ✅ | ✓ | ✓ | 2/2 | got='BRCA1_HUMAN' expected='BRCA1_HUMAN' |
| `ann-02` | protein_annotation | ✅ | ✓ | ✓ | 2/2 | got='Homo sapiens' expected='Homo sapiens' |
| `ann-03` | protein_annotation | ✅ | ✓ | ✓ | 2/2 | summary_len=668 needs=['p53'] |
| `ann-04` | protein_annotation | ✅ | ✓ | ✓ | 1/1 | summary_len=1157 needs=['hemoglobin'] |
| `ann-05` | protein_annotation | ✅ | ✓ | ✓ | 2/2 | got='Cellular tumor antigen p53' contains='p53' |
| `ann-06` | protein_annotation | ✅ | ✓ | ✓ | 1/1 | got='Homo sapiens' expected='Homo sapiens' |
| `mut-01` | mutation_effect | ✅ | ✓ | ✓ | 2/2 | got=1 expected=1 |
| `mut-02` | mutation_effect | ✅ | ✓ | ✓ | 2/2 | got=['class change: hydrophobic → polar_uncharged', 'cysteine gain/loss (disulfi |
| `mut-03` | mutation_effect | ✅ | ✓ | ✓ | 1/1 | got=['class change: positive → negative', 'charge reversal'] contains_any=['char |
| `mut-04` | mutation_effect | ✅ | ✓ | ✓ | 2/2 | got='likely impactful' expected='likely impactful' |
| `mut-05` | mutation_effect | ✅ | ✓ | ✓ | 2/2 | got=1 expected=1 |
| `mut-06` | mutation_effect | ✅ | ✓ | ✓ | 2/2 | got=0 expected=0 |
| `pro-01` | protocol_reasoning | ✅ | ✓ | ✓ | 3/3 | summary_len=745 needs=['p53'] |
| `pro-02` | protocol_reasoning | ✅ | ✓ | ✓ | 2/2 | got=5 min=1 |
| `pro-03` | protocol_reasoning | ✅ | ✓ | ✓ | 1/1 | got='Homo sapiens' expected='Homo sapiens' |
| `pro-04` | protocol_reasoning | ✅ | ✓ | ✓ | 2/2 | got=110 expected=110 |
| `pro-05` | protocol_reasoning | ✅ | ✓ | ✓ | 1/1 | got='MAKL' starts_with='MAK' |
| `pro-06` | protocol_reasoning | ✅ | ✓ | ✓ | 2/2 | got=5 min=1 |
| `wf-01` | workflow | ✅ | ✓ | ✓ | 1/2 | got=[] min_length=0 |
| `wf-02` | workflow | ❌ | ✓ | ✓ | 0/0 | got='' contains='fallback' |
| `wf-03` | workflow | ✅ | ✓ | ✓ | 0/0 | got="original query had 0 hits, used token 'nonexistent' (fallback)" contains='t |
| `wf-04` | workflow | ✅ | ✓ | ✓ | 2/2 | got='protein' expected='protein' |
| `wf-05` | workflow | ✅ | ✓ | ✓ | 2/2 | got=0 expected=0 |
| `wf-06` | workflow | ✅ | ✓ | ✓ | 1/1 | got=5 min=0 |
| `edge-01` | edge_case | ✅ | ✓ | ✓ | 1/1 | got=1 expected=1 |
| `edge-02` | edge_case | ✅ | ✓ | ✓ | 1/1 | got=16 expected=16 |
| `edge-03` | edge_case | ✅ | ✓ | ✓ | 0/0 | got='P0DJN6' min_length=1 |
| `edge-04` | edge_case | ✅ | ✓ | ✓ | 0/0 | got=5 min=0 |
| `followup-01-step1` | follow_up | ✅ | ✓ | ✓ | 1/1 | got='BRCA1_HUMAN' expected='BRCA1_HUMAN' |
| `followup-01-step2` | follow_up | ❌ | ✓ | ✓ | 0/1 | summary_len=837 needs=['BRCA1'] |
| `followup-02-step1` | follow_up | ✅ | ✓ | ✓ | 2/2 | got='protein' expected='protein' |
| `followup-02-step2` | follow_up | ❌ | ✓ | ✓ | 0/0 | summary_len=510 needs=['organism', 'species'] |
| `stress-01` | stress | ✅ | ✓ | ✓ | 1/1 | got=[{'header': 'seq1', 'length': 12, 'type': 'dna', 'composition': {'A': 4, 'T' |
| `stress-02` | stress | ✅ | ✓ | ✓ | 1/1 | got='Cellular tumor antigen p53' contains='p53' |
| `stress-03` | stress | ✅ | ✓ | ✓ | 1/1 | got=5 min=1 |
