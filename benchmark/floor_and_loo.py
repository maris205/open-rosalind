"""Floor/stability and leave-one-skill-out analysis from existing run records.

Round-4 reviewer asked for a *direct* floor statistic to justify the
"stable accuracy floor" language, plus internal-validity sensitivity.

Inputs (must already exist):
  benchmark/scaled_results.json       1,770 runs, 6 models × 5 conditions × 59 tasks (T=0.2, 1 seed)
  benchmark/paired_results_t02.json   1,770 runs, 2 models × 3 conditions × 59 tasks × 5 seeds (T=0.2)
  benchmark/paired_results.json       1,062 runs, 2 models × 3 conditions × 59 tasks × 3 seeds (T=0.7)

Outputs:
  benchmark/floor_stats.md            stability + lower-tail tables
  benchmark/leave_one_out.md          per-skill leave-one-out re-aggregation
"""
from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(path: Path) -> list[dict]:
    return json.loads(path.read_text())


# --------------------------------------------------------------------
# 1. Per-task min-over-seeds (worst seed) and across-seed SD
# --------------------------------------------------------------------
def per_task_seed_stats(records: list[dict]) -> dict:
    """Returns { (model, condition): {tid: {min:_, mean:_, sd:_, max:_, n:_}} }."""
    grouped: dict = defaultdict(lambda: defaultdict(list))
    for r in records:
        k = (r["model"], r["condition"])
        grouped[k][r["task_id"]].append(int(r["metrics"]["accuracy"]))
    out: dict = {}
    for k, by_task in grouped.items():
        d: dict = {}
        for tid, vs in by_task.items():
            d[tid] = {
                "n": len(vs),
                "min": min(vs),
                "mean": sum(vs) / len(vs),
                "sd": statistics.pstdev(vs) if len(vs) > 1 else 0.0,
                "max": max(vs),
            }
        out[k] = d
    return out


def floor_summary(stats: dict, model_filter: list[str] | None = None) -> list[dict]:
    """For each (model, condition):
       - mean_acc = average of per-task means
       - floor_acc = average of per-task mins (worst-seed acc per task)
       - lower_decile = 10th percentile of per-task mean accuracies
       - mean_sd_per_task = average across-seed SD
       - frac_unstable = fraction of tasks with mean SD > 0
       - catastrophic_rate = fraction of tasks with min == 0 (zero seeds correct)
    """
    rows = []
    for (m, c), by_task in sorted(stats.items()):
        if model_filter and m not in model_filter:
            continue
        means = [d["mean"] for d in by_task.values()]
        mins = [d["min"] for d in by_task.values()]
        sds = [d["sd"] for d in by_task.values()]
        if not means:
            continue
        means_sorted = sorted(means)
        n = len(means_sorted)
        decile_idx = max(0, int(0.1 * n) - 1)
        rows.append({
            "model": m, "condition": c,
            "n_tasks": n,
            "mean_acc": sum(means) / n,
            "floor_acc": sum(mins) / n,
            "lower_decile_acc": means_sorted[decile_idx],
            "across_seed_sd": sum(sds) / n,
            "frac_unstable": sum(1 for s in sds if s > 0) / n,
            "catastrophic_rate": sum(1 for v in mins if v == 0) / n,
        })
    return rows


def render_floor_table(rows: list[dict]) -> str:
    if not rows:
        return ""
    md = ["| Model | Condition | n_tasks | mean acc | **floor acc** | lower-decile | mean across-seed SD | unstable% | catastrophic% |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(
            f"| {r['model'].split('/')[-1]} | **{r['condition']}** | {r['n_tasks']} | "
            f"{r['mean_acc']*100:.1f}% | **{r['floor_acc']*100:.1f}%** | "
            f"{r['lower_decile_acc']*100:.1f}% | {r['across_seed_sd']*100:.2f} pp | "
            f"{r['frac_unstable']*100:.1f}% | {r['catastrophic_rate']*100:.1f}% |"
        )
    return "\n".join(md)


# --------------------------------------------------------------------
# 2. Leave-one-skill-out sensitivity
# --------------------------------------------------------------------
SKILL_FOR_TASK = {
    # rough mapping by id prefix in full91.json
    "seq-": "sequence", "ann-": "protein", "lit-": "literature",
    "mut-": "mutation", "pro-": "protein-or-mixed",
    "wf-": "workflow-edge", "edge-": "edge", "stress-": "edge",
    "followup-": "follow-up", "harness-": "multistep",
}


def task_skill(tid: str) -> str:
    for prefix, skill in SKILL_FOR_TASK.items():
        if tid.startswith(prefix):
            return skill
    return "other"


def leave_one_out_aggregate(records: list[dict], model: str) -> list[dict]:
    """Recompute (full, react, no_tool) accuracy on the 59 unique tasks while
    leaving out one skill-category at a time. Uses the seed-mean per task as
    the per-task accuracy to be aggregated."""
    by_cond_task = defaultdict(lambda: defaultdict(list))
    for r in records:
        if r["model"] != model:
            continue
        if r["condition"] not in ("full", "react", "no_tool"):
            continue
        by_cond_task[r["condition"]][r["task_id"]].append(int(r["metrics"]["accuracy"]))
    # Per task: mean across seeds
    means = {c: {tid: sum(vs) / len(vs) for tid, vs in d.items()} for c, d in by_cond_task.items()}
    skills = sorted({task_skill(tid) for tid in means["full"].keys()})
    rows = []
    for held_out in ["(none)"] + skills:
        line = {"held_out": held_out, "n_remaining": 0}
        for c in ("full", "react", "no_tool"):
            ms = [v for tid, v in means[c].items()
                  if held_out == "(none)" or task_skill(tid) != held_out]
            if not ms:
                line[c] = float("nan")
            else:
                line[c] = sum(ms) / len(ms)
                line["n_remaining"] = len(ms)
        # Pairwise gaps
        line["full_minus_react"] = line["full"] - line["react"]
        line["full_minus_no_tool"] = line["full"] - line["no_tool"]
        rows.append(line)
    return rows


def render_loo(rows: list[dict], model: str) -> str:
    md = [f"### Model: `{model}`", "",
          "| Held-out skill | n_remaining | full | react | no_tool | full−react | **full−no_tool** |",
          "|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(
            f"| {r['held_out']} | {r['n_remaining']} | {r['full']*100:.1f}% | {r['react']*100:.1f}% | "
            f"{r['no_tool']*100:.1f}% | {r['full_minus_react']*100:+.1f} pp | "
            f"**{r['full_minus_no_tool']*100:+.1f} pp** |"
        )
    return "\n".join(md)


# --------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------
def main():
    paired_t02 = load(ROOT / "benchmark" / "paired_results_t02.json")
    paired_t07 = load(ROOT / "benchmark" / "paired_results.json")

    # Floor / stability
    stats_t02 = per_task_seed_stats(paired_t02)
    stats_t07 = per_task_seed_stats(paired_t07)

    md = ["# Floor / stability analysis",
          "",
          "Per-task stability statistics computed across seeds, *not* aggregated across tasks.",
          "",
          "**floor acc** = average across tasks of the *worst seed*'s accuracy on that task. "
          "If floor acc is high, the system rarely fails on a task even at its unluckiest sample. "
          "**lower-decile** = the 10th-percentile per-task seed-mean accuracy (i.e. the worst 10% of tasks). "
          "**mean across-seed SD** = average per-task SD across the K seeds. "
          "**unstable%** = fraction of tasks where at least one seed disagreed with another. "
          "**catastrophic%** = fraction of tasks where *every* seed got it wrong.",
          "",
          "## Replication B (5 seeds at T=0.2 — the same temperature as §8.5)",
          "",
          render_floor_table(floor_summary(stats_t02)),
          "",
          "## Replication A (3 seeds at T=0.7 — robustness sidecar)",
          "",
          render_floor_table(floor_summary(stats_t07)),
          ""]
    out_floor = ROOT / "benchmark" / "floor_stats.md"
    out_floor.write_text("\n".join(md))
    print("\n".join(md))
    print(f"\n[floor] saved → {out_floor}")
    print()

    # Leave-one-skill-out (use T=0.2 5-seed records — most data per task)
    md2 = ["# Leave-one-skill-out sensitivity",
           "",
           "How robust are the headline gaps if we delete an entire skill category? "
           "We use Replication B's per-task seed-mean accuracy and recompute "
           "`full`, `react`, `no_tool` aggregates while holding one category out.",
           "",
           "Skill-category mapping by task-id prefix: "
           "`seq-` → sequence · `ann-` → protein · `lit-` → literature · `mut-` → mutation · "
           "`pro-` → protein-or-mixed · `wf-` → workflow-edge · `edge-`/`stress-` → edge · "
           "`followup-` → follow-up · `harness-` → multistep.",
           ""]
    for m in ["google/gemma-4-26b-a4b-it", "openai/gpt-5-mini"]:
        md2 += [render_loo(leave_one_out_aggregate(paired_t02, m), m), ""]
    out_loo = ROOT / "benchmark" / "leave_one_out.md"
    out_loo.write_text("\n".join(md2))
    print("\n".join(md2))
    print(f"\n[loo] saved → {out_loo}")


if __name__ == "__main__":
    main()
