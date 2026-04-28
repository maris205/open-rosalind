---
name: mutation_effect
description: >
  Analyze mutations by comparing wild-type and mutant sequences.
  Use this skill when:
  (1) User provides WT and MT sequences,
  (2) User asks about mutation impact (e.g., "p.R175H"),
  (3) User wants to compare two sequences,
  (4) User asks "what's the difference between these sequences".
license: MIT
category: mutation-analysis
tags: [mutation, variant, sequence-comparison, hgvs]
---

# Mutation Effect Analysis

Compare wild-type and mutant sequences to identify mutations.

## When to Use

- User provides WT and MT sequences
- User asks about mutation impact (p.R175H)
- User wants to compare two sequences
- User asks "what's the difference"

## Workflow

### Step 1: Parse Input

Extract WT and MT sequences from user input:
```
WT: MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGP
MT: p.R175H
```
or
```
WT: ATCG
MT: ATGG
```

### Step 2: Compute Differences

```python
from open_rosalind.skills_v2.mutation import tools

diff = tools.diff(wt="MEEPQ", mt="MEEPQ")
# Returns: {n_differences: 0, positions: [], changes: [], severity: "none"}

diff = tools.diff(wt="MEEPQ", mt="MEEPH")
# Returns: {n_differences: 1, positions: [4], changes: ["Q→H"], severity: "moderate"}
```

### Step 3: Classify Impact

Rule-based classification:
- Charge reversal (K→E, R→D): **high**
- Hydrophobic→polar (V→S): **moderate**
- Conservative (I→L): **low**
- Synonymous: **none**

### Step 4: Return Evidence-Grounded Result

```python
return {
    "annotation": {
        "kind": "mutation",
        "n_differences": 1,
        "severity": "moderate"
    },
    "confidence": 0.75,
    "notes": [],
    "mutation": diff  # Full diff object (evidence)
}
```

## Expected Outputs

| Field | Description |
|-------|-------------|
| `n_differences` | Number of mutations |
| `positions` | List of mutation positions |
| `changes` | List of changes (e.g., "Q→H") |
| `severity` | Impact level (none/low/moderate/high) |
| `properties` | Property changes (charge, hydrophobicity) |

## Design Principles

1. **Tool-first**: All data from `mutation.diff` tool
2. **Evidence-grounded**: Return full `mutation` object
3. **Traceable**: Diff computation logged
4. **Fail-safe**: Invalid sequences → confidence=0.0

## Fallback Strategy

If sequences are identical:
- Return n_differences=0
- severity="none"
- Log to `notes`
