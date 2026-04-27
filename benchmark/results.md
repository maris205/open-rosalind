# Mini BioBench v0 — Results

- Tasks: **26**
- Accuracy (semantic check): **100.0%**
- Skill routed correctly:    **100.0%**
- Expected tools called:     **100.0%**
- Has trace:                 **100.0%**
- Has evidence:              **100.0%**

## By category

| Category | n | Accuracy | Skill correct | Tool called |
|---|---|---|---|---|
| sequence | 8 | 100% | 100% | 100% |
| literature | 6 | 100% | 100% | 100% |
| annotation | 6 | 100% | 100% | 100% |
| mutation | 6 | 100% | 100% | 100% |

## Per-task results

| ID | Cat | Pass | Skill ok | Tool ok | Conf | Reason |
|---|---|---|---|---|---|---|
| `seq-01` | sequence | ✅ | ✓ | ✓ | 0.20 | got='dna' expected='dna' |
| `seq-02` | sequence | ✅ | ✓ | ✓ | 0.20 | got='protein' expected='protein' |
| `seq-03` | sequence | ✅ | ✓ | ✓ | 0.20 | got=49 expected=49 |
| `seq-04` | sequence | ✅ | ✓ | ✓ | 0.20 | got=71.43 approx=71.43 tol=0.5 |
| `seq-05` | sequence | ✅ | ✓ | ✓ | 0.20 | got='MRT*' starts_with='MRT' |
| `seq-06` | sequence | ✅ | ✓ | ✓ | 0.20 | got='TTACGTACGCAT' starts_with='TTACGT' |
| `seq-07` | sequence | ✅ | ✓ | ✓ | 0.20 | got=1 expected=1 |
| `seq-08` | sequence | ✅ | ✓ | ✓ | 0.20 | got='dna' expected='dna' |
| `lit-01` | literature | ✅ | ✓ | ✓ | 0.85 | got=5 min=1 |
| `lit-02` | literature | ✅ | ✓ | ✓ | 0.85 | got=5 min=1 |
| `lit-03` | literature | ✅ | ✓ | ✓ | 0.85 | got=5 min=1 |
| `lit-04` | literature | ✅ | ✓ | ✓ | 0.85 | got=5 min=1 |
| `lit-05` | literature | ✅ | ✓ | ✓ | 0.85 | got=5 min=1 |
| `lit-06` | literature | ✅ | ✓ | ✓ | 0.85 | got=5 min=1 |
| `ann-01` | annotation | ✅ | ✓ | ✓ | 0.95 | got='BRCA1_HUMAN' expected='BRCA1_HUMAN' |
| `ann-02` | annotation | ✅ | ✓ | ✓ | 0.95 | got='Homo sapiens' expected='Homo sapiens' |
| `ann-03` | annotation | ✅ | ✓ | ✓ | 0.95 | summary_len=797 needs=['p53'] |
| `ann-04` | annotation | ✅ | ✓ | ✓ | 0.95 | summary_len=1198 needs=['hemoglobin'] |
| `ann-05` | annotation | ✅ | ✓ | ✓ | 0.95 | got='Cellular tumor antigen p53' contains='p53' |
| `ann-06` | annotation | ✅ | ✓ | ✓ | 0.95 | got='Homo sapiens' expected='Homo sapiens' |
| `mut-01` | mutation | ✅ | ✓ | ✓ | 0.70 | got=1 expected=1 |
| `mut-02` | mutation | ✅ | ✓ | ✓ | 0.85 | got=['class change: hydrophobic → polar_uncharged', 'cysteine gain/loss (disulfi |
| `mut-03` | mutation | ✅ | ✓ | ✓ | 0.85 | got=['class change: positive → negative', 'charge reversal'] contains_any=['char |
| `mut-04` | mutation | ✅ | ✓ | ✓ | 0.85 | got='likely impactful' expected='likely impactful' |
| `mut-05` | mutation | ✅ | ✓ | ✓ | 0.70 | got=1 expected=1 |
| `mut-06` | mutation | ✅ | ✓ | ✓ | 0.50 | got=0 expected=0 |
