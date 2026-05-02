"""Scaled ablation: full 59 tasks × 5 conditions × N models.

Reuses condition implementations from run_pilot.py.
Parallelism: ThreadPoolExecutor across (task, condition, model) jobs.

Outputs:
  benchmark/scaled_results.json   per-run records
  benchmark/scaled_summary.md     aggregate tables (overall + per-split + per-model)

Usage:
  python benchmark/run_scaled.py \
      --tasks benchmark/full91.json \
      --models google/gemma-4-26b-a4b-it,deepseek/deepseek-chat \
      --workers 8
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from open_rosalind.backends import OpenRouterBackend

# Reuse condition implementations + scoring + helpers
from benchmark.run_pilot import CONDITIONS, score, run_one  # noqa: E402

OUT_JSON = ROOT / "benchmark" / "scaled_results.json"
OUT_MD = ROOT / "benchmark" / "scaled_summary.md"


def wilson_ci(p: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95% CI."""
    if n == 0:
        return (0.0, 0.0)
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    halfw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - halfw), min(1.0, centre + halfw))


def aggregate(rows: list[dict]) -> dict:
    n = len(rows)
    if n == 0:
        return {"n": 0}
    avg = lambda key: sum(r["metrics"][key] for r in rows) / n  # noqa: E731
    return {
        "n": n,
        "accuracy": avg("accuracy"),
        "tool_correctness": avg("tool_correctness"),
        "citation_presence": avg("citation_presence"),
        "trace_completeness": avg("trace_completeness"),
        "no_fail": avg("no_fail"),
        "avg_latency_ms": int(sum(r["latency_ms"] for r in rows) / n),
    }


def fmt_pct(p: float, n: int) -> str:
    lo, hi = wilson_ci(p, n)
    return f"{p*100:.1f}% [{lo*100:.0f},{hi*100:.0f}]"


def run_one_with_model(task: dict, cond: str, model: str) -> dict:
    backend = OpenRouterBackend(model=model)
    try:
        r = CONDITIONS[cond](task, backend)
        err = None
    except Exception as e:
        r = {"summary": f"[{type(e).__name__}: {e}]", "tool_path": [],
             "trace_steps": [], "trace_complete": False}
        err = traceback.format_exc()
    metrics = score(task, r)
    return {
        "task_id": task["id"], "split": task["split"], "condition": cond, "model": model,
        "input": task["input"], "summary": r["summary"][:2000],
        "tool_path": r["tool_path"], "metrics": metrics,
        "latency_ms": 0, "error": err,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default=str(ROOT / "benchmark" / "full91.json"))
    ap.add_argument("--models", default="google/gemma-4-26b-a4b-it")
    ap.add_argument("--conditions", default=",".join(CONDITIONS.keys()))
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    tasks = json.loads(Path(args.tasks).read_text())
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    conds = [c.strip() for c in args.conditions.split(",") if c.strip()]

    jobs = [(t, c, m) for t in tasks for c in conds for m in models]
    print(f"[scaled] {len(tasks)} tasks × {len(conds)} conditions × {len(models)} models = {len(jobs)} runs",
          flush=True)
    print(f"[scaled] models: {models}", flush=True)
    print(f"[scaled] conditions: {conds}", flush=True)

    results: list[dict] = []
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_one_with_model, t, c, m): (t["id"], c, m) for t, c, m in jobs}
        done = 0
        for fut in as_completed(futs):
            tid, c, m = futs[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = {"task_id": tid, "split": "?", "condition": c, "model": m,
                     "input": "", "summary": f"[runner-error: {e}]",
                     "tool_path": [], "metrics": {"accuracy": False, "tool_correctness": False,
                                                  "citation_presence": False, "trace_completeness": False,
                                                  "no_fail": False},
                     "latency_ms": 0, "error": str(e)}
            results.append(r)
            done += 1
            if done % 20 == 0 or done == len(jobs):
                print(f"[scaled] {done}/{len(jobs)}  elapsed={int(time.time()-t_start)}s", flush=True)

    OUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2))

    # === Aggregate ===
    md: list[str] = ["# Scaled ablation results",
                     "",
                     f"Tasks: {len(tasks)} · Conditions: {len(conds)} · Models: {len(models)}",
                     f"Total runs: {len(results)}",
                     ""]

    # Overall × condition (averaged across models)
    md += ["## Overall — averaged across all models, all splits", "",
           "| Condition | n | Accuracy | ToolCorr | CitePres | TraceComp | NoFail |",
           "|---|---|---|---|---|---|---|"]
    for c in conds:
        rows = [r for r in results if r["condition"] == c]
        a = aggregate(rows)
        if a["n"] == 0:
            continue
        md.append(
            f"| **{c}** | {a['n']} | {fmt_pct(a['accuracy'], a['n'])} | "
            f"{fmt_pct(a['tool_correctness'], a['n'])} | {fmt_pct(a['citation_presence'], a['n'])} | "
            f"{fmt_pct(a['trace_completeness'], a['n'])} | {fmt_pct(a['no_fail'], a['n'])} |"
        )

    # Per-model × condition
    for m in models:
        md += ["", f"## Model: `{m}`", "",
               "| Condition | n | Accuracy | ToolCorr | CitePres | TraceComp | NoFail |",
               "|---|---|---|---|---|---|---|"]
        for c in conds:
            rows = [r for r in results if r["condition"] == c and r["model"] == m]
            a = aggregate(rows)
            if a["n"] == 0:
                continue
            md.append(
                f"| **{c}** | {a['n']} | {fmt_pct(a['accuracy'], a['n'])} | "
                f"{fmt_pct(a['tool_correctness'], a['n'])} | {fmt_pct(a['citation_presence'], a['n'])} | "
                f"{fmt_pct(a['trace_completeness'], a['n'])} | {fmt_pct(a['no_fail'], a['n'])} |"
            )

    # Per-split × condition (one model = first model, the reference)
    ref_m = models[0]
    md += ["", f"## Per-split breakdown (model: `{ref_m}`)", ""]
    for sp in ["basic", "edge", "multistep"]:
        md += [f"### split: {sp}", "",
               "| Condition | n | Accuracy | ToolCorr | CitePres |",
               "|---|---|---|---|---|"]
        for c in conds:
            rows = [r for r in results if r["condition"] == c and r["model"] == ref_m and r["split"] == sp]
            a = aggregate(rows)
            if a["n"] == 0:
                continue
            md.append(
                f"| **{c}** | {a['n']} | {fmt_pct(a['accuracy'], a['n'])} | "
                f"{fmt_pct(a['tool_correctness'], a['n'])} | {fmt_pct(a['citation_presence'], a['n'])} |"
            )
        md.append("")

    OUT_MD.write_text("\n".join(md) + "\n")
    print("\n" + "\n".join(md))
    print(f"\n[scaled] saved → {OUT_JSON}, {OUT_MD}")


if __name__ == "__main__":
    main()
