---
name: literature_search
description: >
  Search PubMed for biomedical research papers by topic, disease, or gene.
  Use this skill when:
  (1) User asks to find papers about a topic,
  (2) User wants recent literature on a disease or gene,
  (3) User needs citations for research,
  (4) User asks "papers about X" or "literature on Y".
license: MIT
category: knowledge-retrieval
tags: [pubmed, literature, papers, citations]
---

# Literature Search

Search PubMed for biomedical research papers.

## When to Use

- User asks "find papers about CRISPR"
- User wants recent literature on a disease/gene
- User needs citations or references
- User asks "papers about X" or "literature on Y"

## Workflow

### Step 1: Parse Query

Extract search terms from user input:
- Topic: "CRISPR base editing"
- Disease: "Alzheimer's disease"
- Gene: "BRCA1 mutations"

### Step 2: Search PubMed

```python
from open_rosalind.skills_v2.literature import tools

results = tools.search(query="CRISPR base editing", max_results=5)
# Returns: {hits: [{pmid, title, authors, abstract, date, doi}, ...]}
```

### Step 3: Return Evidence-Grounded Result

```python
return {
    "annotation": {
        "kind": "literature",
        "query": "CRISPR base editing",
        "n_hits": len(results["hits"]),
        "top_pmids": [h["pmid"] for h in results["hits"][:3]]
    },
    "confidence": 0.8,
    "notes": [],
    "pubmed": results  # Full search results (evidence)
}
```

## Expected Outputs

| Field | Description |
|-------|-------------|
| `pmid` | PubMed ID |
| `title` | Paper title |
| `authors` | Author list |
| `abstract` | Full abstract |
| `date` | Publication date |
| `doi` | DOI identifier |
| `link` | PubMed URL |

## Design Principles

1. **Tool-first**: All data from `pubmed.search` API
2. **Evidence-grounded**: Return full `pubmed` object
3. **Traceable**: API calls logged to trace
4. **Fail-safe**: Empty results → confidence=0.0, logged to notes

## Fallback Strategy

If query returns 0 hits:
1. Remove year filters
2. Try broader terms
3. Log fallback to `notes`
