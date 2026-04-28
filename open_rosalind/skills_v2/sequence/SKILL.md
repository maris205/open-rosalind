---
name: sequence_basic_analysis
description: Analyze DNA/RNA/protein sequences and optionally probe UniProt for homology. Use when user provides FASTA format or raw sequence.
category: sequence
safety_level: safe
tools_used: [sequence.analyze, uniprot.search]
---

# Sequence Basic Analysis

Analyze biological sequence: $ARGUMENTS

## Input

- **sequence** (required): FASTA format or raw DNA/RNA/protein sequence

## Output

Returns structured analysis:
- `annotation`: Sequence metadata (kind, type, length)
- `confidence`: 0.7-0.85 depending on type
- `sequence_stats`: Detailed statistics per record
- `uniprot_hint`: Optional homology probe results (protein ≥25aa)

## Workflow

### Step 1: Parse and Analyze Sequence

Call `sequence.analyze` tool (local BioPython):

```python
from open_rosalind.skills_v2.sequence import tools

stats = tools.analyze(sequence)
# Returns: {records: [{type, length, gc_content, translation, ...}], n_records}
```

For each record:
- Detect type (DNA/RNA/protein)
- Compute length, composition
- DNA: GC%, translation, reverse complement
- Protein: molecular weight

### Step 2: Optional UniProt Probe (Protein ≥25aa)

If primary sequence is protein and length ≥25aa:

1. Extract probe fragment (30aa or full sequence if shorter)
2. Call `uniprot.search` with probe
3. Aggregate top hits into `uniprot_hint`

```python
probe = primary_sequence[:30]
result = uniprot_search(query=probe)
uniprot_hint = {
    "hits": len(result["hits"]),
    "top_match": result["hits"][0]["accession"],
    "probe_length": 30
}
```

### Step 3: Return Evidence-Grounded Result

Construct response following Open-Rosalind principles:
- `annotation`: Structured metadata (no free-form text)
- `confidence`: Rule-based score (0.85 for DNA/RNA, 0.7 for protein)
- `notes`: Fallback messages (e.g., "UniProt probe: 3 hits")
- `sequence_stats`: Full tool output (evidence)
- `uniprot_hint`: Probe results (evidence)

## Examples

### Example 1: DNA Sequence

**Input**:
```json
{"sequence": "ATGGCCAAATTAA"}
```

**Output**:
```json
{
  "annotation": {"kind": "sequence", "primary_type": "dna", "length": 13},
  "confidence": 0.85,
  "sequence_stats": {
    "records": [{
      "type": "dna",
      "length": 13,
      "gc_content": 30.77,
      "translation": "MAKL*",
      "reverse_complement": "TTAATTTGGCCAT"
    }]
  }
}
```

### Example 2: Protein with UniProt Probe

**Input**:
```json
{"sequence": "MVKVGVNGFGRIGRLVTRA"}
```

**Output**:
```json
{
  "annotation": {"kind": "sequence", "primary_type": "protein", "length": 19},
  "confidence": 0.7,
  "notes": ["UniProt probe: 3 hits"],
  "sequence_stats": {
    "records": [{
      "type": "protein",
      "length": 19,
      "molecular_weight": 1.95
    }]
  },
  "uniprot_hint": {
    "hits": 3,
    "top_match": "Q9H3P7",
    "probe_length": 19
  }
}
```

## Design Principles

Following Open-Rosalind core principles:

1. **Tool-first**: All facts from `sequence.analyze` and `uniprot.search` tools
2. **Evidence-grounded**: `sequence_stats` and `uniprot_hint` are raw tool outputs
3. **Traceable**: Every tool call logged to trace
4. **Fail-safe**: UniProt probe failure doesn't crash skill (logged to `notes`)

## Notes

- Multi-FASTA supported (splits on `>` headers)
- UniProt probe only for protein ≥25aa (avoids false positives)
- Probe uses 30aa fragment (balance between specificity and coverage)
- Local computation (BioPython) is fast and deterministic
