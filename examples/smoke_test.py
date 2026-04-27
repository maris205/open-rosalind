"""End-to-end smoke test: runs the agent on three demo prompts."""
from __future__ import annotations

import json

from open_rosalind.backends import build_backend
from open_rosalind.config import load_config
from open_rosalind.orchestrator import Agent

DEMOS = [
    "What is BRCA1 and where is it located in the cell?",
    "Find recent papers about CRISPR base editing in 2024",
    "P38398",
]


def main():
    cfg = load_config()
    agent = Agent(build_backend(cfg["backend"]), trace_dir=cfg.get("trace", {}).get("dir", "./traces"))
    for q in DEMOS:
        print(f"\n=== {q} ===")
        out = agent.analyze(q)
        print(f"skill: {out['skill']}  session: {out['session_id']}")
        print(out["summary"][:600])
        print(f"trace: {out['trace_path']}")


if __name__ == "__main__":
    main()
