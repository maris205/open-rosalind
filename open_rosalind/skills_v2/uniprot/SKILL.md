---
name: uniprot_lookup
description: >
  Query UniProt database for protein information including function, organism, sequence, and structure.
  Use this skill when:
  (1) User provides a UniProt accession (e.g., P38398, Q9H3P7),
  (2) User asks about a protein by name (e.g., "BRCA1", "hemoglobin"),
  (3) User wants protein function, organism, or sequence information,
  (4) User needs to find similar proteins by sequence search.
license: MIT
category: protein-annotation
tags: [uniprot, protein, annotation, sequence-search]
---

# UniProt Lookup

Query UniProt database for protein annotation and homology search.

## When to Use

- User provides a UniProt accession (P38398, Q9H3P7)
- User asks about a protein by name ("BRCA1", "p53")
- User wants protein function, organism, or sequence
- User needs to find similar proteins

## Workflow

### Step 1: Determine Query Type

**If user provides accession** (e.g., "P38398"):
- Use `uniprot.fetch` to get full entry

**If user provides protein name** (e.g., "BRCA1"):
- Use `uniprot.search` with name as query
- Extract top hit accession
- Fetch full entry

### Step 2: Fetch UniProt Entry

```python
from open_rosalind.skills_v2.uniprot import tools

# Fetch by accession
entry = tools.fetch(accession="P38398")
# Returns: {id, accession, name, organism, function, sequence, ...}
```

### Step 3: Optional Homology Search

If user asks "find similar proteins":

```python
# Search by sequence fragment
results = tools.search(query="MVKVGVNGFGRIGRLVTRA")
# Returns: {hits: [{accession, name, organism, score}, ...]}
```

### Step 4: Return Evidence-Grounded Result

```python
return {
    "annotation": {
        "kind": "protein",
        "accession": entry["accession"],
        "name": entry["name"],
        "organism": entry["organism"]
    },
    "confidence": 0.9,
    "notes": [],
    "entry": entry  # Full UniProt entry (evidence)
}
```

## Expected Outputs

### Fetch Result
| Field | Description |
|-------|-------------|
| `id` | UniProt ID (e.g., BRCA1_HUMAN) |
| `accession` | Primary accession (P38398) |
| `name` | Protein name |
| `organism` | Source organism |
| `function` | Protein function description |
| `sequence` | Amino acid sequence |
| `length` | Sequence length |

### Search Result
| Field | Description |
|-------|-------------|
| `hits` | List of matching proteins |
| `accession` | UniProt accession |
| `name` | Protein name |
| `organism` | Source organism |
| `score` | Match score (0-1) |

## Design Principles

Following Open-Rosalind core principles:

1. **Tool-first**: All data from `uniprot.fetch` and `uniprot.search` tools
2. **Evidence-grounded**: Return full `entry` object (raw API response)
3. **Traceable**: Every API call logged to trace
4. **Fail-safe**: API errors logged to `notes`, don't crash skill

## Fallback Strategy

If direct accession fetch fails:
1. Try token-based search (extract protein name from query)
2. Use top hit from search results
3. Log fallback to `notes`

## Examples

See `examples/` directory for:
- `fetch_by_accession.json` — Direct accession lookup
- `search_by_name.json` — Protein name search
- `homology_search.json` — Sequence-based search
