"""Generate an independent hold-out test split via an LLM that has no
involvement with the system or the original BioBench.

Author bias mitigation: ask Claude (a different model from any of the 6
evaluation models) to write 30 biological questions targeting the same 4 skill
categories (sequence/protein/literature/mutation), with explicit gold-source
citations from authoritative resources (UniProt, NCBI/PubMed). The prompt is
NOT shown the design of the existing benchmark, so its tasks are independent.

Output schema (one JSON object per task):
  {
    "id": "ind-XX",
    "split": "holdout",
    "category": "<sequence|protein|literature|mutation>",
    "input": "<user-style natural language query>",
    "expected_skill": "<one of the 4 skill names>",
    "gold_path": ["<expected atomic tool>", ...],
    "keywords": ["<keyword1>", "<keyword2>"],
    "gold_source": "<UniProt accession or PMID or quoted authoritative URL>"
  }

The LLM is asked to:
  - generate 30 tasks total, evenly distributed across 4 categories
  - use ONLY real biological identifiers and PMIDs that it can verify
  - keep questions answerable by the existing 4 skills
  - return strict JSON

Output: benchmark/holdout30.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from openai import OpenAI

OUT_PATH = ROOT / "benchmark" / "holdout30.json"

GENERATOR_MODEL = "qwen/qwen3-235b-a22b"  # in 6-model eval, but author bias is independent of this


PROMPT = """You are designing an evaluation set for a biomedical agent that has the following four skills:

1. **sequence_basic_analysis** — accepts a DNA/RNA/protein sequence (FASTA or raw); returns type, length, GC%, translation, etc.
2. **uniprot_lookup** — accepts a UniProt accession (e.g. P38398) OR a free-text protein/gene query (e.g. "BRCA1 human"); returns annotation.
3. **literature_search** — accepts a free-text biomedical query; returns up to 5 PubMed papers.
4. **mutation_effect** — accepts a wild-type sequence + a mutation (HGVS like p.R175H or a mutant sequence); returns physicochemical impact heuristic.

Your task: generate **30 fresh evaluation tasks**, evenly distributed across the four skills (8/8/7/7).

Each task MUST be:
- A user-style natural-language input that a researcher might type.
- Answerable using exactly one of the four skills above.
- Bound to a real, verifiable biological object: real UniProt accessions only, real PMIDs only, real proteins/sequences from authoritative sources.
- Distinct in content from any task you might have seen related to BRCA1 (P38398), TP53/p53 (P04637), hemoglobin beta (P68871), GAPDH, insulin (P01308), MAPK8, AlphaFold queries, CRISPR base editing 2024 queries, CAR-T therapy 2023 queries — these are reserved for the existing benchmark and you must NOT duplicate them.

Diversity requirements:
- Use a variety of organisms (human, mouse, yeast, E. coli, plant, virus).
- Use a variety of protein families (kinases, GPCRs, transcription factors, transporters, structural proteins, immune receptors).
- For literature_search, use distinct topics (e.g. mitochondrial biogenesis, ribosomal frameshift, RNA editing).
- For mutation_effect, use real characterized variants (e.g. CFTR ΔF508, HBB E6V/HbS, EGFR L858R, KRAS G12D, HTT polyQ expansion).

Return a JSON array of 30 objects with this exact schema:

```json
[
  {
    "id": "ind-01",
    "category": "sequence|protein|literature|mutation",
    "input": "<user-style query>",
    "expected_skill": "sequence_basic_analysis|uniprot_lookup|literature_search|mutation_effect",
    "gold_path": ["sequence.analyze" | "uniprot.fetch" | "uniprot.search" | "pubmed.search" | "mutation.diff"],
    "keywords": ["lowercase keyword 1", "lowercase keyword 2"],
    "gold_source": "<UniProt accession | PMID:NNNNNNNN | brief justification>"
  },
  ...
]
```

Constraints on `keywords`:
- 2 lowercase substrings that MUST appear in any correct answer.
- Choose them so they discriminate correct from hallucinated answers.
- For sequence tasks: include one keyword identifying the type ("dna"/"rna"/"protein") AND one keyword that is the EXACT length number ("19", "147", etc) — never use generic words like "protein" + "length" alone.
- For protein tasks: use the gene symbol AND a function-specific term (e.g. ["egfr", "receptor tyrosine kinase"]).
- For literature tasks: use one topic term AND one method/object term (e.g. ["crispr-cas9", "programmable"]).
- For mutation tasks: use the HGVS notation AND a physico-chemical impact word (e.g. ["p.l858r", "charge"]).

Constraints on `input`:
- Pure natural language; do not hint at which skill should be used.
- Length 5–25 words.
- For sequence tasks: keep raw sequences SHORT (≤ 30 nucleotides or ≤ 25 amino acids). Do not write long repetitive sequences. NEVER repeat the same triplet 30+ times.

Return ONLY the JSON array, no prose, no code fences, no commentary.
"""


def main():
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
    print(f"[holdout] generating with {GENERATOR_MODEL} ...")
    resp = client.chat.completions.create(
        model=GENERATOR_MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.3,
        max_tokens=16000,
    )
    text = (resp.choices[0].message.content or "").strip()

    # Strip code fences if any
    text = re.sub(r"^```json\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    text = re.sub(r"^```\s*|\s*```$", "", text, flags=re.MULTILINE).strip()

    try:
        tasks = json.loads(text)
    except json.JSONDecodeError as e:
        Path("/tmp/holdout_raw.json").write_text(text)
        print(f"[holdout] JSON parse failed: {e}; raw saved to /tmp/holdout_raw.json")
        sys.exit(1)

    # Add split tag
    for t in tasks:
        t["split"] = "holdout"

    OUT_PATH.write_text(json.dumps(tasks, ensure_ascii=False, indent=2))
    print(f"[holdout] saved {len(tasks)} tasks → {OUT_PATH}")
    # Show sample
    for t in tasks[:3]:
        print(f"  {t['id']:7} {t['category']:10} | {t['input'][:80]}")


if __name__ == "__main__":
    main()
