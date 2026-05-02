"""Seeded paired experiment.

Goal: paired statistical evidence for the central claim (tool-first invariant matters).

Design:
  - 3 seeds (T=0.7) × 3 conditions (full / react / no_tool) × 2 models × 59 tasks = 1,062 runs
  - Models: Gemma-4-26B-a4b (deployment target) and GPT-5-mini (the model where ReAct collapsed)
  - Per-task outcome under each (cond, seed, model) is binary accuracy (0/1)
  - For each (model, seed) we compute paired McNemar between:
      full vs react    (does constraint help?)
      full vs no_tool  (does tool-first help?)
  - We then aggregate: 3-seed mean accuracy ± std, plus combined McNemar.

The lift over Section 8.5 is paired statistical significance and seed variance:
"single run per cell at T=0.2" was Gpt-5.4 reviewer's main statistical objection.

Outputs:
  benchmark/paired_results.json
  benchmark/paired_summary.md
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

from openai import OpenAI

# Reuse condition implementations
import benchmark.run_pilot as RP  # noqa: E402
from open_rosalind.backends import OpenRouterBackend
from open_rosalind.tools import REGISTRY as TOOL_REGISTRY

OUT_JSON = ROOT / "benchmark" / "paired_results.json"
OUT_MD = ROOT / "benchmark" / "paired_summary.md"

CONDITIONS = ["full", "react", "no_tool"]


# ----------------------------------------------------------------------
# Backend with temperature/seed override
# ----------------------------------------------------------------------
class SeededBackend(OpenRouterBackend):
    """OpenRouter backend that accepts a per-instance seed and temperature."""

    def __init__(self, model: str, *, seed: int, temperature: float = 0.7, **kw):
        super().__init__(model=model, **kw)
        self._seed = seed
        self._temp = temperature

    def chat(self, messages, *, temperature=None, max_tokens=1024, **kwargs):
        # Always override with seed+temperature; ignore caller's defaults
        extra_body = {}
        if self.reasoning_enabled:
            extra_body["reasoning"] = {"enabled": True}
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self._temp,
            max_tokens=max_tokens,
            seed=self._seed,
            extra_body=extra_body or None,
        )
        msg = resp.choices[0].message
        content = (msg.content or "").strip()
        if not content:
            reasoning = getattr(msg, "reasoning", None) or ""
            if not reasoning:
                details = getattr(msg, "reasoning_details", None) or []
                if isinstance(details, list):
                    reasoning = "\n".join(
                        (d.get("text") or d.get("summary") or "") if isinstance(d, dict) else str(d)
                        for d in details
                    ).strip()
            content = reasoning.strip()
        from open_rosalind.backends.base import ChatResponse
        return ChatResponse(content=content, raw=resp.model_dump() if hasattr(resp, "model_dump") else None)


# ----------------------------------------------------------------------
# ReAct re-implementation that uses the seeded backend
# ----------------------------------------------------------------------
def run_react_seeded(task: dict, backend: SeededBackend) -> dict:
    """Same as run_pilot.run_react but uses backend's seed/temp."""
    client: OpenAI = backend.client
    tools_schema = RP._tool_schema_openai()
    msgs = [
        {"role": "system", "content": RP.REACT_SYSTEM},
        {"role": "user", "content": task["input"]},
    ]
    tool_path: list[str] = []
    trace_steps: list[dict] = []
    summary = ""
    for hop in range(6):
        try:
            resp = client.chat.completions.create(
                model=backend.model, messages=msgs, tools=tools_schema,
                tool_choice="auto", temperature=backend._temp, max_tokens=800,
                seed=backend._seed,
            )
        except Exception as e:
            summary = f"[react backend error: {e}]"
            break
        m = resp.choices[0].message
        if m.tool_calls:
            msgs.append({
                "role": "assistant",
                "content": m.content or "",
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in m.tool_calls
                ],
            })
            for tc in m.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                t0 = time.time()
                result = RP._call_tool(tc.function.name, args)
                latency_ms = int((time.time() - t0) * 1000)
                tool_path.append(tc.function.name.replace("_", ".", 1))
                trace_steps.append({
                    "skill": tc.function.name.replace("_", ".", 1),
                    "input": args, "output": result,
                    "latency_ms": latency_ms,
                    "status": "error" if isinstance(result, dict) and result.get("error") else "success",
                })
                msgs.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False)[:4000],
                })
        else:
            summary = (m.content or "").strip()
            break
    else:
        summary = "[react: max hops reached without final answer]"
    return {"summary": summary, "tool_path": tool_path,
            "trace_steps": trace_steps, "trace_complete": bool(trace_steps)}


CONDITIONS_FN = {
    "full": RP.run_full,
    "react": run_react_seeded,
    "no_tool": RP.run_no_tool,
}


def run_one(task: dict, cond: str, model: str, seed: int, temperature: float = 0.7) -> dict:
    backend = SeededBackend(model=model, seed=seed, temperature=temperature)
    t0 = time.time()
    try:
        r = CONDITIONS_FN[cond](task, backend)
        err = None
    except Exception as e:
        r = {"summary": f"[{type(e).__name__}: {e}]", "tool_path": [],
             "trace_steps": [], "trace_complete": False}
        err = traceback.format_exc()
    latency = int((time.time() - t0) * 1000)
    metrics = RP.score(task, r)
    return {
        "task_id": task["id"], "split": task["split"], "condition": cond,
        "model": model, "seed": seed,
        "summary": r["summary"][:1500],
        "tool_path": r["tool_path"], "metrics": metrics,
        "latency_ms": latency, "error": err,
    }


# ----------------------------------------------------------------------
# Statistics
# ----------------------------------------------------------------------
def mcnemar(b: int, c: int) -> tuple[float, float]:
    """Continuity-corrected McNemar's chi-square. Returns (chi2, two-sided p).
    b = #(A correct, B wrong); c = #(A wrong, B correct).
    """
    if b + c == 0:
        return 0.0, 1.0
    chi2 = (abs(b - c) - 1) ** 2 / (b + c)
    # P(chi^2_1 >= x) via survival fn of standard normal² = erfc(sqrt(x/2))
    p = math.erfc(math.sqrt(chi2 / 2))
    return chi2, p


def paired_table(results: list[dict], model: str, cond_a: str, cond_b: str) -> dict:
    """Build per-task McNemar table aggregated across seeds."""
    by_task = {}  # task_id -> (a_correct_count, b_correct_count, n_seeds)
    seeds = sorted({r["seed"] for r in results if r["model"] == model})
    for seed in seeds:
        for r in results:
            if r["model"] != model or r["seed"] != seed:
                continue
            tid = r["task_id"]
            by_task.setdefault(tid, {"a": [], "b": []})
            if r["condition"] == cond_a:
                by_task[tid]["a"].append(int(r["metrics"]["accuracy"]))
            elif r["condition"] == cond_b:
                by_task[tid]["b"].append(int(r["metrics"]["accuracy"]))
    # Per-(task,seed) pairs
    pairs = []
    for tid, d in by_task.items():
        for ai, bi in zip(d["a"], d["b"]):
            pairs.append((ai, bi))
    a_only = sum(1 for ai, bi in pairs if ai == 1 and bi == 0)
    b_only = sum(1 for ai, bi in pairs if ai == 0 and bi == 1)
    both = sum(1 for ai, bi in pairs if ai == 1 and bi == 1)
    neither = sum(1 for ai, bi in pairs if ai == 0 and bi == 0)
    chi2, p = mcnemar(a_only, b_only)
    return {
        "n_pairs": len(pairs),
        "both_correct": both,
        "a_only": a_only, "b_only": b_only,
        "neither": neither,
        "acc_a": (both + a_only) / max(len(pairs), 1),
        "acc_b": (both + b_only) / max(len(pairs), 1),
        "mcnemar_chi2": chi2, "p_value": p,
    }


def per_seed_acc(results: list[dict]) -> dict:
    """Returns {(model, condition, seed): accuracy}."""
    out = {}
    by = {}
    for r in results:
        k = (r["model"], r["condition"], r["seed"])
        by.setdefault(k, []).append(int(r["metrics"]["accuracy"]))
    for k, vs in by.items():
        out[k] = sum(vs) / len(vs)
    return out


def summarize(results: list[dict], models: list[str], seeds: list[int]) -> str:
    md = ["# Seeded paired ablation",
          "",
          f"Tasks: {len(set(r['task_id'] for r in results))} unique · "
          f"Conditions: {len(CONDITIONS)} · Models: {len(models)} · Seeds: {len(seeds)} (T=0.7)",
          f"Total runs: {len(results)}",
          ""]

    # Per-seed accuracy table
    md += ["## Accuracy by seed (mean across all 59 tasks)", "",
           "| Model | Condition | seed=" + " | seed=".join(str(s) for s in seeds) + " | mean | std |",
           "|" + "---|" * (3 + len(seeds) + 2)]
    accs = per_seed_acc(results)
    for m in models:
        for c in CONDITIONS:
            row = [m.split("/")[-1], c]
            vals = []
            for s in seeds:
                v = accs.get((m, c, s))
                if v is None:
                    row.append("—")
                else:
                    vals.append(v)
                    row.append(f"{v*100:.1f}%")
            mean = sum(vals) / len(vals) if vals else 0
            std = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5 if vals else 0
            row.append(f"{mean*100:.1f}%")
            row.append(f"{std*100:.1f}")
            md.append("| " + " | ".join(row) + " |")

    # Paired McNemar — full vs react, full vs no_tool, per model
    md += ["", "## Paired McNemar tests (across all seeds combined)", ""]
    for m in models:
        md += [f"### Model: `{m}`", "",
               "| Comparison | n_pairs | acc_A | acc_B | A-only | B-only | both | neither | χ² | p |",
               "|---|---|---|---|---|---|---|---|---|---|"]
        for cond_a, cond_b in [("full", "react"), ("full", "no_tool"), ("react", "no_tool")]:
            t = paired_table(results, m, cond_a, cond_b)
            md.append(
                f"| {cond_a} vs {cond_b} | {t['n_pairs']} | "
                f"{t['acc_a']*100:.1f}% | {t['acc_b']*100:.1f}% | "
                f"{t['a_only']} | {t['b_only']} | {t['both_correct']} | {t['neither']} | "
                f"{t['mcnemar_chi2']:.2f} | {t['p_value']:.2e} |"
            )
        md.append("")

    return "\n".join(md) + "\n"


# ----------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default=str(ROOT / "benchmark" / "full91.json"))
    ap.add_argument("--models", default="google/gemma-4-26b-a4b-it,openai/gpt-5-mini")
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--out-tag", default="")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    tag = f"_{args.out_tag}" if args.out_tag else ""
    out_json = ROOT / "benchmark" / f"paired_results{tag}.json"
    out_md = ROOT / "benchmark" / f"paired_summary{tag}.md"

    tasks = json.loads(Path(args.tasks).read_text())
    models = [m.strip() for m in args.models.split(",")]
    seeds = [int(s) for s in args.seeds.split(",")]

    jobs = [(t, c, m, s) for t in tasks for c in CONDITIONS for m in models for s in seeds]

    # Resume from checkpoint if present
    results: list[dict] = []
    done_keys: set = set()
    if out_json.exists():
        try:
            results = json.loads(out_json.read_text())
            for r in results:
                done_keys.add((r["task_id"], r["condition"], r["model"], r["seed"]))
            print(f"[paired] resuming with {len(results)} prior results", flush=True)
        except Exception:
            results = []
    jobs = [(t, c, m, s) for t, c, m, s in jobs if (t["id"], c, m, s) not in done_keys]
    print(f"[paired] {len(tasks)} tasks × {len(CONDITIONS)} cond × {len(models)} models × {len(seeds)} seeds | "
          f"T={args.temperature} | remaining={len(jobs)}", flush=True)
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_one, t, c, m, s, args.temperature): (t["id"], c, m, s) for t, c, m, s in jobs}
        done = 0
        for fut in as_completed(futs):
            try:
                r = fut.result()
            except Exception as e:
                tid, c, m, s = futs[fut]
                r = {"task_id": tid, "split": "?", "condition": c, "model": m, "seed": s,
                     "summary": f"[runner-error: {e}]", "tool_path": [],
                     "metrics": {"accuracy": False, "tool_correctness": False,
                                 "citation_presence": False, "trace_completeness": False,
                                 "no_fail": False},
                     "latency_ms": 0, "error": str(e)}
            results.append(r)
            done += 1
            if done % 50 == 0 or done == len(jobs):
                print(f"[paired] {done}/{len(jobs)}  elapsed={int(time.time()-t_start)}s", flush=True)
                # checkpoint
                out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2))

    out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    md = summarize(results, models, seeds)
    out_md.write_text(md)
    print("\n" + md)
    print(f"[paired] saved → {out_json}, {out_md}")


if __name__ == "__main__":
    main()
