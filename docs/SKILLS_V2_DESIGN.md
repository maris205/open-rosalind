# Skills v2 Architecture Design

> **Modular, extensible, community-friendly skills structure**

Inspired by Claude skills (`/root/.claude/skills`) and DeerFlow skills (`/root/deer-flow/skills/public`), while maintaining Open-Rosalind's design principles.

---

## Directory Structure

```
skills_v2/
├── sequence/
│   ├── SKILL.md              # Main documentation (frontmatter + workflow)
│   ├── skill.json            # Metadata (schema, examples, safety)
│   ├── handler.py            # Skill handler (pipeline logic)
│   ├── tools.py              # Tool functions (BioPython, local computation)
│   ├── scripts/              # Optional: standalone scripts
│   │   └── batch_analyze.py  # Example: batch processing
│   ├── examples/             # Test cases
│   │   ├── dna.json
│   │   └── protein.json
│   └── README.md             # User-facing documentation (optional)
├── uniprot/
│   ├── SKILL.md
│   ├── skill.json
│   ├── handler.py
│   ├── tools.py              # uniprot.fetch, uniprot.search
│   └── examples/
├── literature/
│   ├── SKILL.md
│   ├── skill.json
│   ├── handler.py
│   ├── tools.py              # pubmed.search
│   └── examples/
├── mutation/
│   ├── SKILL.md
│   ├── skill.json
│   ├── handler.py
│   ├── tools.py              # mutation.diff
│   └── examples/
└── __init__.py               # Auto-discovery registry
```

---

## File Purposes

### SKILL.md (Required)

Claude-style skill documentation with frontmatter:

```markdown
---
name: sequence_basic_analysis
description: Analyze DNA/RNA/protein sequences...
category: sequence
safety_level: safe
tools_used: [sequence.analyze, uniprot.search]
---

# Sequence Basic Analysis

## Workflow
### Step 1: Parse and Analyze
### Step 2: Optional UniProt Probe
### Step 3: Return Evidence-Grounded Result

## Examples
## Design Principles
```

### skill.json (Required)

Structured metadata for programmatic access:

```json
{
  "name": "sequence_basic_analysis",
  "version": "1.0.0",
  "category": "sequence",
  "safety_level": "safe",
  "input_schema": {...},
  "output_schema": {...},
  "examples": [...],
  "tools_used": ["sequence.analyze", "uniprot.search"],
  "mcp_compatible": true
}
```

### handler.py (Required)

Skill pipeline logic:

```python
def handler(payload: dict, trace: Any) -> dict:
    """
    Main skill handler.
    
    Args:
        payload: Input from user/harness
        trace: Trace logger
        
    Returns:
        {annotation, confidence, notes, evidence}
    """
    # Step 1: Call tools
    # Step 2: Aggregate evidence
    # Step 3: Return structured result
```

### tools.py (Required)

Atomic tool functions (local computation or API calls):

```python
def analyze(sequence: str) -> dict:
    """Analyze sequence using BioPython."""
    # Pure function, no side effects
    # Returns structured data
```

### scripts/ (Optional)

Standalone scripts for batch processing, utilities, etc.:

```python
# scripts/batch_analyze.py
"""Batch process multiple FASTA files."""
import argparse
# Can be called from CLI or SKILL.md workflow
```

### examples/ (Optional but Recommended)

Test cases for validation:

```json
{
  "input": {"sequence": "ATGGCC"},
  "expected_output": {"annotation": {"kind": "sequence", "type": "dna"}}
}
```

---

## Comparison: Claude vs DeerFlow vs Open-Rosalind

| Aspect | Claude Skills | DeerFlow Skills | Open-Rosalind v2 |
|---|---|---|---|
| **Structure** | SKILL.md only | SKILL.md + scripts/ + agents/ | SKILL.md + skill.json + handler.py + tools.py |
| **Metadata** | Frontmatter only | Frontmatter only | Frontmatter + skill.json |
| **Code** | Inline in SKILL.md | scripts/ directory | handler.py + tools.py |
| **Sub-agents** | No | agents/ directory | No (use Harness) |
| **Examples** | Inline in SKILL.md | No | examples/ directory |
| **MCP** | Compatible | Compatible | Compatible + extended |

---

## Design Principles (Open-Rosalind)

1. **Tool-first**: All facts from tools (tools.py)
2. **Evidence-grounded**: handler.py returns raw tool outputs
3. **Traceable**: Every tool call logged
4. **Fail-safe**: Errors don't crash skill (logged to notes)
5. **Modular**: Each skill is self-contained
6. **Community-friendly**: Standard format (SKILL.md + skill.json)

---

## Auto-Discovery Registry

`__init__.py` scans subdirectories and auto-registers skills:

```python
from pathlib import Path
import json

SKILLS = {}

for skill_dir in Path(__file__).parent.iterdir():
    if skill_dir.is_dir() and (skill_dir / "skill.json").exists():
        meta = json.loads((skill_dir / "skill.json").read_text())
        handler_module = __import__(f"{__name__}.{skill_dir.name}.handler", fromlist=["handler"])
        
        SKILLS[meta["name"]] = Skill(
            name=meta["name"],
            handler=handler_module.handler,
            **meta
        )
```

---

## Migration Plan (MVP3.1)

1. ✅ Create skills_v2/ structure
2. ✅ Complete sequence/ skill (full example)
3. 🔜 Complete uniprot/ skill
4. 🔜 Complete literature/ skill
5. 🔜 Complete mutation/ skill
6. 🔜 Implement auto-discovery registry
7. 🔜 Update server.py to use skills_v2
8. 🔜 Run BioBench v0/v1/v0.3 to verify no regression
9. 🔜 Deprecate old skills/ module

---

## Benefits

1. **Easy to add new skills**: Copy template, fill in SKILL.md + handler.py
2. **Community contributions**: Standard format, clear documentation
3. **MCP compatible**: Can be exposed as MCP tools
4. **Testable**: examples/ directory for validation
5. **Maintainable**: Each skill is isolated, no cross-dependencies
6. **Discoverable**: Auto-registry scans subdirectories

---

## Next Steps

Complete remaining 3 skills (uniprot, literature, mutation) following the sequence/ template.
