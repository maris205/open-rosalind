# Skill Specification v1.0

> **Standard interface for bio-agent tools**

Every skill in Open-Rosalind conforms to this specification, enabling programmatic discovery, composition, and testing.

---

## Skill Schema

```python
@dataclass
class Skill:
    name: str                          # Unique identifier (snake_case)
    description: str                   # Human-readable summary (1-2 sentences)
    category: str                      # One of: sequence | annotation | literature | mutation | meta
    input_schema: dict                 # JSON Schema for payload argument
    output_schema: dict                # JSON Schema for returned evidence dict
    handler: Callable[[dict, Any], dict]  # (payload, trace) -> evidence
    examples: list[dict]               # [{input, expects}, ...]
    safety_level: str                  # safe | network | compute | exec
    tools_used: list[str]              # Tool names this skill may call
```

---

## Registered Skills (MVP2)

| Name | Category | Tools | Safety | Description |
|---|---|---|---|---|
| `sequence_basic_analysis` | sequence | `sequence.analyze`, `uniprot.search` | network | Compute stats on DNA/RNA/protein; probe UniProt for homology |
| `uniprot_lookup` | annotation | `uniprot.fetch`, `uniprot.search` | network | Resolve accession or free-text query to structured annotation |
| `literature_search` | literature | `pubmed.search` | network | Retrieve PubMed articles; clean query; fallback on empty year filter |
| `mutation_effect` | mutation | `mutation.diff` | safe | Compare WT vs MT; annotate physico-chemical impact |

---

## Input Schema

Skills accept a `payload: dict` argument. The shape is defined by `input_schema` (JSON Schema).

**Example** (`uniprot_lookup`):
```json
{
  "type": "object",
  "properties": {
    "query": {"type": "string"},
    "accession": {"type": "string", "description": "Optional explicit UniProt ID"}
  },
  "required": ["query"]
}
```

---

## Output Schema

Skills return an `evidence: dict`. The shape is defined by `output_schema`.

**Standard fields** (all skills):
- `annotation: dict` — Structured metadata (kind, name, organism, function, ...)
- `confidence: float` — Rule-based score ∈ [0, 1]
- `notes: list[str]` — Fallback messages, warnings, or empty-result explanations

**Skill-specific fields**:
- `sequence_basic_analysis`: `sequence_stats`, `uniprot_hint`
- `uniprot_lookup`: `entry`, `search`
- `literature_search`: `pubmed`
- `mutation_effect`: `mutation`

---

## Examples

Every skill declares 1-3 examples:

```python
examples=[
    {"input": {"query": "P38398", "accession": "P38398"}, "expects": "BRCA1_HUMAN"},
    {"input": {"query": "What is hemoglobin?"}, "expects": "search hits including HBA_HUMAN"},
]
```

Examples serve as:
- **Documentation** for users (`open-rosalind skills inspect <name>`)
- **Test cases** for CI
- **Few-shot prompts** for LLM-assisted routing

---

## Safety Levels

| Level | Meaning | Example |
|---|---|---|
| `safe` | Pure computation, no I/O | `mutation.diff` (local sequence comparison) |
| `network` | External API calls | `uniprot.fetch`, `pubmed.search` |
| `compute` | Heavy local compute (>1s) | BLAST, Foldseek (future) |
| `exec` | Arbitrary code execution | Python REPL, shell (future) |

Safety levels enable:
- **Sandboxing**: `exec` skills run in isolated containers
- **Rate limiting**: `network` skills respect API quotas
- **User consent**: UI can prompt before calling `exec` skills

---

## Handler Signature

```python
def handler(payload: dict, trace: Trace) -> dict:
    """
    Args:
        payload: Validated input matching input_schema
        trace: Trace logger (call trace.log(kind, data))
    
    Returns:
        evidence: dict matching output_schema, always includes:
            - annotation: dict
            - confidence: float
            - notes: list[str] (optional)
    """
```

**Contract**:
- Handler must **never raise** — wrap tool calls in error-safe `_run()`
- Handler must **always return** a dict with `annotation` + `confidence`
- Handler must **log all tool calls** to trace

---

## Tool Calls

Skills compose atomic tools via `_run(tool_name, trace, **kwargs)`:

```python
result = _run("uniprot.fetch", trace, accession="P38398")
if _is_error(result):
    notes.append(f"uniprot.fetch failed: {result['error']['message']}")
```

`_run()` guarantees:
- Returns `{error: ...}` on failure (never raises)
- Logs `tool_call` + `tool_result` events to trace
- Records `latency_ms` + `status` (success | error)

---

## Fallback Strategies

Skills must handle empty results gracefully:

**Example** (`uniprot_lookup`):
1. Try cleaned query
2. If 0 hits → retry with each significant token
3. If still 0 → log to `notes`, return empty annotation with `confidence=0.0`

**Example** (`literature_search`):
1. Try query with year filter `2024[dp]`
2. If 0 hits → drop year, retry
3. If still 0 → log to `notes`, return empty with `confidence=0.0`

---

## Annotation Schema

Every skill returns `annotation: dict` with a `kind` field:

```python
# Protein annotation
{"kind": "protein", "accession": "P38398", "name": "...", "organism": "...", "function": "...", "length": 1863}

# Literature annotation
{"kind": "literature", "n_hits": 5, "top_pmids": [...], "query_used": "..."}

# Mutation annotation
{"kind": "mutation", "n_differences": 1, "overall_assessment": "likely impactful", "notable_flags": [...]}
```

The UI renders annotation in a structured card (not raw JSON).

---

## Confidence Scoring

Rule-based heuristics per skill:

| Scenario | Confidence |
|---|---|
| Exact accession fetch | 0.95 |
| Search with ≥3 hits | 0.7–0.85 |
| Fallback retry succeeded | 0.5–0.6 |
| Empty result | 0.0 |
| Tool error | 0.0 |

Confidence is **not** a model probability — it's a signal of data quality.

---

## CLI

```bash
# List all skills
open-rosalind skills list

# Inspect one skill (shows schema + examples)
open-rosalind skills inspect uniprot_lookup

# Output as JSON
open-rosalind skills list --json
```

---

## API

```bash
# List skills
GET /api/skills
→ {"skills": [{"name": "...", "category": "...", "tools_used": [...], ...}]}

# Get full spec
GET /api/skills/uniprot_lookup
→ {"name": "...", "input_schema": {...}, "output_schema": {...}, "examples": [...]}
```

---

## Extending

To add a new skill:

1. **Define handler** in `skills/_pipelines.py`
2. **Declare Skill** in `skills/__init__.py`:
   ```python
   MY_SKILL = Skill(
       name="my_skill",
       category="...",
       description="...",
       input_schema={...},
       output_schema={...},
       handler=my_skill_handler,
       examples=[...],
       safety_level="network",
       tools_used=["tool.foo"],
   )
   ```
3. **Register** in `SKILLS` dict
4. **Add tests** in `tests/`
5. **Update BioBench** if needed

---

## Summary

This spec defines a **standard bio-agent skill interface** that is:
- **Discoverable** (CLI + API)
- **Composable** (uniform I/O)
- **Testable** (examples + schema validation)
- **Extensible** (third parties can add skills)

**For paper**: This constitutes a **reusable tool abstraction** for scientific agents.
