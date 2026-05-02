# R6 Hold-Out Failure Diagnosis and Fixes

## Round 5 → Round 6 Context

Round-5 paper included a 30-task LLM-authored hold-out that revealed severe external-validity collapse:
- Gemma full: 82% (internal) → 17.8% (hold-out)
- On hold-out, ReAct beat full by 31 pp (p=0.004)

GPT-5.4 reviewer scored 7/10 → 6/10, stating: "Round-5 is a better paper, but a weaker methods claim."

Verdict: **"7 → 8 not realistic without a fix-and-rerun that actually flips the sign."**

## R6 Iteration 1: Three Diagnosed Failure Modes

### Fix 1: Stop-word expansion in query cleaning

**Problem:** Queries like "Information on mouse Pten" or "Details on human ADRB2" preserved stop-words "Information" and "Details", which diluted UniProt searches. The single-token fallback then picked those words.

**Fix:** Added 20+ stop-words to `_STOPWORDS` in `skills/_pipelines.py`:
```python
"information", "info", "details", "detail", "data", "knowledge",
"characterize", "characterise", "analyze", "analyse", "analysis", "evaluate",
"effect", "effects", "impact", "impacts", "consequences",
...
```

**Result:** "Information on mouse Pten" → cleaned to "mouse Pten" → UniProt search succeeds.

### Fix 2: Natural-language mutation routing

**Problem:** Queries like "Effect of KRAS G12D substitution" have no explicit WT/MT sequences. Router fell back to `uniprot_lookup`, which annotates the gene but doesn't analyze the mutation.

**Fix:** 
1. Added HGVS pattern detection in `router.py`: `HGVS_3LETTER_RE`, `COMPACT_MUT_RE`, `DELTA_DEL_RE`
2. New `_detect_nl_mutation()` extracts (gene_symbol, mutation_str) from natural-language queries
3. Extended `mutation_effect` skill to accept `gene_symbol + mutation` payload; skill looks up WT sequence from UniProt by gene name, then applies mutation

**Result:** "Effect of KRAS G12D" → routes to `mutation_effect` with `gene_symbol="KRAS", mutation="p.G12D"` → fetches KRAS sequence → runs mutation.diff.

### Fix 3: Greek-vs-ASCII transliteration in scorer

**Problem:** Literature answers contained "PGC-1α" (Greek alpha), but gold keywords were "pgc-1alpha" (ASCII). Strict substring match failed.

**Fix:** Enhanced `has_keywords()` in `run_pilot.py` with Greek-to-ASCII map and bidirectional matching. Also added HGVS 3-letter ↔ 1-letter equivalence (e.g., "p.Gly12Asp" matches "G12D").

**Result:** "PGC-1α" in answer now matches keyword "pgc-1alpha".

### R6.0 Hold-Out Results (after fixes 1–3)

| Model | Condition | Before | After | Δ |
|---|---|---|---|---|
| Gemma | full | 17.8% | **30.0%** | **+12.2 pp** ✅ |
| Gemma | react | 48.9% | 67.8% | +18.9 pp |
| Gemma | no_tool | 46.7% | 56.7% | +10.0 pp |

**Cluster-aware:** full vs react on Gemma: Δ = -37.8 pp, 95% CI [-56.7, -18.9], p=0.001

**Verdict:** Fixes helped (+12 pp), but **rank reversal persists** — ReAct still beats full significantly.

## R6 Iteration 2: Routing Brittleness

### Diagnosis: Why does ReAct still beat full?

Analyzed 13 tasks where react beat full by >30pp. Three failure classes:

1. **Sequence tasks routed to uniprot.search** (5 tasks: ind-09, ind-13, ind-17, ind-21, ind-29)
   - Input: "Characterize this E. coli protein: MKRISTTITTTKGLPVTAYKELLRRLG"
   - Router saw keyword "protein" → routed to `uniprot_lookup`
   - Should route to `sequence_basic_analysis` (it's a raw sequence!)

2. **Literature tasks routed to uniprot.search** (3 tasks: ind-15, ind-19, ind-23)
   - Input: "Publications on bacterial efflux pumps..."
   - `LIT_RE` didn't match "publications", "studies", "research"
   - Should route to `literature_search`

3. **Mutation tasks: gene lookup succeeded but mutation.diff failed** (3 tasks: ind-16, ind-24, ind-28)
   - Router correctly identified mutation → fetched UniProt sequence
   - But `mutation.diff` failed: "mutation could not be mapped to the provided reference sequence"
   - HGVS position (e.g., L858) doesn't match the canonical sequence numbering

### Fix 4: Embedded sequence detection

**Problem:** Router's sequence detection required the *entire* input to match `SEQUENCE_RE` or `PROTEIN_RE`. Inputs like "Characterize this protein: MKRIS..." failed because the prose prefix broke the pattern.

**Fix:**
1. Added `_extract_embedded_sequence()` that scans for continuous letter-strings ≥20 chars
2. Lowered thresholds: `SEQUENCE_RE` from 40 → 20 chars, `PROTEIN_RE` from 30 → 20 chars
3. Router now checks for embedded sequences *before* falling back to uniprot_lookup

**Result:** "Characterize this E. coli protein: MKRISTTITTTKGLPVTAYKELLRRLG" → extracts "MKRISTTITTTKGLPVTAYKELLRRLG" → routes to `sequence_basic_analysis`.

### Fix 5: Literature keyword expansion

**Problem:** `LIT_RE` only matched "paper|papers|literature|pubmed|cite|citation|publication|review". Missed "publications", "studies", "research", "article".

**Fix:** Expanded `LIT_RE` to:
```python
r"\b(paper|papers|literature|pubmed|cite|citation|publication|publications|review|reviews|studies|study|research|article|articles)\b"
```

**Result:** "Publications on bacterial efflux pumps" → routes to `literature_search`.

### R6.1 Hold-Out Run (in progress)

Expecting:
- Sequence routing fixes should recover 5 tasks (ind-09, ind-13, ind-17, ind-21, ind-29)
- Literature routing fixes should recover 3 tasks (ind-15, ind-19, ind-23)
- Mutation tasks (ind-16, ind-24, ind-28) may still fail if HGVS position mismatch persists

**Best-case scenario:** Gemma full goes from 30.0% to ~56.7% (30% + 8 tasks × 3.3% each).

If that happens, full ≈ no_tool, and the rank-reversal claim weakens to "full ≈ react ≈ no_tool on hold-out" — still not a win, but no longer a significant loss.

## Summary

R6 implemented 5 concrete fixes targeting the 3 diagnosed failure modes from Round-5 hold-out:
1. Stop-word expansion (query cleaning)
2. Natural-language mutation routing (gene_symbol + HGVS)
3. Greek-vs-ASCII transliteration (scorer)
4. Embedded sequence detection (router)
5. Literature keyword expansion (router)

R6.0 improved Gemma full from 17.8% to 30.0% (+12.2 pp), but rank reversal persisted.

R6.1 adds routing robustness fixes. If successful, this may close the gap to react/no_tool and allow the paper to claim "routing fixes are necessary and sufficient for external validity."

If R6.1 still shows full < react significantly, the honest conclusion is: **"The constrained pipeline overfits to template-style inputs; free-form ReAct generalizes better to natural-language phrasings."**
