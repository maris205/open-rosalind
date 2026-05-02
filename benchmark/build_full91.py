"""Build benchmark/full91.json from biobench_v0/v1/v03 jsonl files.

Each output record:
  { id, split, input, expected_skill, gold_path, keywords }

split labels: basic | edge | multistep
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
B = ROOT / "benchmark"

SKILL_TO_TEMPLATE = {
    "harness_protein_research": "protein_research",
    "harness_literature_review": "literature_review",
    "harness_mutation_assessment": "mutation_assessment",
}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def make(rec: dict, split: str) -> dict:
    cat = rec.get("category", "")
    skill = rec.get("expected_skill") or SKILL_TO_TEMPLATE.get(cat, cat)
    return {
        "id": rec["id"],
        "split": split,
        "input": rec["input"],
        "expected_skill": skill,
        "gold_path": rec.get("expected_tools", []) or [],
        "keywords": rec.get("expected_keywords", []) or [],
    }


def main():
    tasks: list[dict] = []
    seen: set[str] = set()

    # v0 = basic (32)
    for rec in load_jsonl(B / "biobench_v0.jsonl"):
        t = make(rec, "basic")
        tasks.append(t)
        seen.add(t["id"])

    # v1 = edge (only the *new* ones beyond v0); the JSONL repeats v0 tasks
    for rec in load_jsonl(B / "biobench_v1.jsonl"):
        if rec["id"] in seen:
            continue
        t = make(rec, "edge")
        tasks.append(t)
        seen.add(t["id"])

    # v03 = multistep (10)
    for rec in load_jsonl(B / "biobench_v03.jsonl"):
        if rec["id"] in seen:
            continue
        t = make(rec, "multistep")
        tasks.append(t)
        seen.add(t["id"])

    out = B / "full91.json"
    out.write_text(json.dumps(tasks, ensure_ascii=False, indent=2))
    by_split: dict[str, int] = {}
    for t in tasks:
        by_split[t["split"]] = by_split.get(t["split"], 0) + 1
    print(f"[build] {len(tasks)} tasks → {out}")
    print(f"[build] split: {by_split}")


if __name__ == "__main__":
    main()
