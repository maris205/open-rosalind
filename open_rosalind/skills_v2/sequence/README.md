# Sequence Basic Analysis

> **Category**: sequence  
> **Safety**: safe (local computation)

Analyzes DNA/RNA/protein sequences and optionally probes UniProt for homology.

---

## Description

Computes basic statistics on biological sequences:
- Type detection (DNA, RNA, protein)
- Length, composition, GC content
- Translation (DNA → protein)
- Reverse complement (DNA)
- Molecular weight (protein)

Optionally probes UniProt with a short fragment to find similar proteins.

---

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "sequence": {
      "type": "string",
      "description": "FASTA format or raw sequence"
    }
  },
  "required": ["sequence"]
}
```

---

## Output Schema

```json
{
  "type": "object",
  "properties": {
    "annotation": {
      "type": "object",
      "properties": {
        "kind": {"const": "sequence"},
        "n_records": {"type": "integer"},
        "primary_type": {"enum": ["dna", "rna", "protein"]}
      }
    },
    "confidence": {"type": "number"},
    "notes": {"type": "array", "items": {"type": "string"}},
    "sequence_stats": {"type": "object"},
    "uniprot_hint": {"type": "object"}
  }
}
```

---

## Examples

### Example 1: DNA sequence

**Input**:
```json
{
  "sequence": "ATGGCCAAATTAA"
}
```

**Output**:
```json
{
  "annotation": {"kind": "sequence", "n_records": 1, "primary_type": "dna"},
  "confidence": 0.85,
  "sequence_stats": {
    "records": [{
      "type": "dna",
      "length": 13,
      "gc_content": 30.77,
      "translation": "MAKL*"
    }]
  }
}
```

### Example 2: Protein sequence with UniProt probe

**Input**:
```json
{
  "sequence": "MVKVGVNGFGRIGRLVTRA"
}
```

**Output**:
```json
{
  "annotation": {"kind": "sequence", "n_records": 1, "primary_type": "protein"},
  "confidence": 0.7,
  "sequence_stats": {
    "records": [{
      "type": "protein",
      "length": 19,
      "molecular_weight": 1.95
    }]
  },
  "uniprot_hint": {
    "hits": 3,
    "top_match": "Q9H3P7"
  }
}
```

---

## Tools Used

- `sequence.analyze` — Local sequence analysis (BioPython)
- `uniprot.search` — Optional homology probe (UniProt API)

---

## Safety Level

**safe** — Pure local computation, no external API calls (unless probe is triggered)

---

## Usage

```python
from open_rosalind.skills_v2.sequence import SEQUENCE_BASIC_ANALYSIS

result = SEQUENCE_BASIC_ANALYSIS.handler(
    {"sequence": "ATGGCCAAATTAA"},
    trace
)
```

---

## Notes

- Multi-FASTA supported (splits on `>` headers)
- UniProt probe only triggered for protein sequences ≥25aa
- Probe uses 30aa fragment (or shorter if sequence is short)
