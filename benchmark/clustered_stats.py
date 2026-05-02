"""Cluster-aware paired analysis of paired_results.json (and t02 replication).

Round 3 reviewer pointed out the bug in run_paired.py's McNemar:
  "McNemar on 177 paired observations = 59 tasks × 3 seeds treats repeated
   runs of the same task as if they were fully independent pairs."

This script provides three corrected analyses:

  1. Task-level McNemar:
       For each task, take the per-task majority (≥ ceil(K/2) of K seeds correct).
       This collapses K seeds to a single binary outcome, so the McNemar pairs
       are independent across tasks.

  2. Clustered permutation test:
       Test statistic = mean(acc_A) - mean(acc_B) across all (task, seed) pairs.
       Null = randomly swap A/B *within each task* (preserves task-level cluster
       structure). 10k permutations. Two-sided p-value.

  3. Mixed-effects-like estimate via cluster-bootstrap:
       Resample tasks (clusters) with replacement; within each resampled task,
       use all its seed-runs. Compute mean(acc_A - acc_B) and a bootstrap CI.

Usage:
    python benchmark/clustered_stats.py --in benchmark/paired_results.json
    python benchmark/clustered_stats.py --in benchmark/paired_results_t02.json --tag t02
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent


def mcnemar(b: int, c: int) -> tuple[float, float]:
    if b + c == 0:
        return 0.0, 1.0
    chi2 = (abs(b - c) - 1) ** 2 / (b + c)
    p = math.erfc(math.sqrt(chi2 / 2))
    return chi2, p


def load(path: Path) -> list[dict]:
    return json.loads(path.read_text())


def by_task_seed(results: list[dict], model: str) -> dict:
    """Returns {task_id: {condition: {seed: bool}}} for one model."""
    out: dict = defaultdict(lambda: defaultdict(dict))
    for r in results:
        if r["model"] != model:
            continue
        out[r["task_id"]][r["condition"]][r["seed"]] = bool(r["metrics"]["accuracy"])
    return out


def task_level_mcnemar(d: dict, cond_a: str, cond_b: str) -> dict:
    """Collapse K seeds to a per-task majority vote, then run McNemar on
    independent task-level pairs."""
    a_only = b_only = both = neither = 0
    a_acc = b_acc = 0
    n = 0
    for tid, conds in d.items():
        if cond_a not in conds or cond_b not in conds:
            continue
        seeds_a = list(conds[cond_a].values())
        seeds_b = list(conds[cond_b].values())
        if not seeds_a or not seeds_b:
            continue
        ka = sum(1 for v in seeds_a if v)
        kb = sum(1 for v in seeds_b if v)
        # majority: > K/2 → 1
        a = ka * 2 > len(seeds_a)
        b = kb * 2 > len(seeds_b)
        if a and not b:
            a_only += 1
        elif b and not a:
            b_only += 1
        elif a and b:
            both += 1
        else:
            neither += 1
        a_acc += int(a)
        b_acc += int(b)
        n += 1
    chi2, p = mcnemar(a_only, b_only)
    return {
        "n_tasks": n, "both": both, "a_only": a_only, "b_only": b_only, "neither": neither,
        "acc_a": a_acc / max(n, 1), "acc_b": b_acc / max(n, 1),
        "chi2": chi2, "p": p,
    }


def clustered_permutation(d: dict, cond_a: str, cond_b: str,
                          n_perm: int = 10000, rng: random.Random | None = None) -> dict:
    """Test mean(A - B) across all (task, seed) pairs.
    Permutation null: independently per task, swap A↔B with probability 0.5.
    """
    rng = rng or random.Random(0)
    pairs_by_task: dict = {}
    for tid, conds in d.items():
        if cond_a not in conds or cond_b not in conds:
            continue
        a = list(conds[cond_a].values())
        b = list(conds[cond_b].values())
        k = min(len(a), len(b))
        if k == 0:
            continue
        # pair seed-aligned values
        seeds_a = sorted(conds[cond_a].keys())
        seeds_b = sorted(conds[cond_b].keys())
        common = sorted(set(seeds_a) & set(seeds_b))
        if not common:
            continue
        pairs_by_task[tid] = [(int(conds[cond_a][s]), int(conds[cond_b][s])) for s in common]

    # Observed
    flat = [(a, b) for ps in pairs_by_task.values() for a, b in ps]
    if not flat:
        return {"n_pairs": 0, "n_tasks": 0, "mean_diff": 0, "p": 1.0}
    obs_diff = mean(a - b for a, b in flat)

    n_extreme = 0
    for _ in range(n_perm):
        diff_sum = 0.0
        n_total = 0
        for ps in pairs_by_task.values():
            swap = rng.random() < 0.5
            for a, b in ps:
                if swap:
                    a, b = b, a
                diff_sum += a - b
                n_total += 1
        d_perm = diff_sum / n_total
        if abs(d_perm) >= abs(obs_diff) - 1e-12:
            n_extreme += 1

    return {
        "n_pairs": len(flat), "n_tasks": len(pairs_by_task),
        "mean_diff": obs_diff, "p": (n_extreme + 1) / (n_perm + 1),
    }


def cluster_bootstrap(d: dict, cond_a: str, cond_b: str,
                      n_boot: int = 5000, rng: random.Random | None = None) -> dict:
    """Bootstrap resample tasks; within each resampled task, average the seed
    diffs. Returns mean and 95% CI of mean(A - B)."""
    rng = rng or random.Random(0)
    task_diffs: dict = {}
    for tid, conds in d.items():
        if cond_a not in conds or cond_b not in conds:
            continue
        common = sorted(set(conds[cond_a].keys()) & set(conds[cond_b].keys()))
        if not common:
            continue
        diffs = [int(conds[cond_a][s]) - int(conds[cond_b][s]) for s in common]
        task_diffs[tid] = mean(diffs)
    if not task_diffs:
        return {"n_tasks": 0, "mean_diff": 0, "ci_lo": 0, "ci_hi": 0}
    tids = list(task_diffs.keys())
    obs_mean = mean(task_diffs.values())
    boot_means = []
    for _ in range(n_boot):
        sample = [task_diffs[rng.choice(tids)] for _ in tids]
        boot_means.append(mean(sample))
    boot_means.sort()
    lo = boot_means[int(0.025 * n_boot)]
    hi = boot_means[int(0.975 * n_boot)]
    return {"n_tasks": len(tids), "mean_diff": obs_mean, "ci_lo": lo, "ci_hi": hi}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    results = load(Path(args.inp))
    models = sorted({r["model"] for r in results})
    seeds = sorted({r["seed"] for r in results})

    md: list[str] = [
        f"# Cluster-aware paired analysis ({args.inp})",
        "",
        f"Tasks: {len(set(r['task_id'] for r in results))} unique · "
        f"Models: {len(models)} · Seeds: {len(seeds)} (`{seeds}`)",
        "",
        "Three analyses, each correcting the unit-of-analysis issue in run_paired.py's McNemar:",
        "",
        "1. **Task-level McNemar (per-task majority vote across seeds)** — independent pairs only.",
        "2. **Cluster permutation test** — null permutes A↔B per task, preserving cluster structure.",
        "3. **Cluster bootstrap** — resample tasks (with all their seeds) for a 95% CI on mean(A − B).",
        "",
    ]

    for m in models:
        d = by_task_seed(results, m)
        md += [f"## Model: `{m}`", ""]
        for cond_a, cond_b in [("full", "react"), ("full", "no_tool"), ("react", "no_tool")]:
            tlm = task_level_mcnemar(d, cond_a, cond_b)
            cp = clustered_permutation(d, cond_a, cond_b)
            cb = cluster_bootstrap(d, cond_a, cond_b)
            md += [
                f"### {cond_a} vs {cond_b}",
                "",
                f"**Task-level McNemar** (n_tasks={tlm['n_tasks']}, "
                f"acc_A={tlm['acc_a']*100:.1f}%, acc_B={tlm['acc_b']*100:.1f}%, "
                f"A-only={tlm['a_only']}, B-only={tlm['b_only']}, both={tlm['both']}, neither={tlm['neither']}): "
                f"χ² = {tlm['chi2']:.2f}, p = {tlm['p']:.2e}",
                "",
                f"**Cluster permutation** (n_tasks={cp['n_tasks']}, mean(A−B) = {cp['mean_diff']*100:+.1f} pp): "
                f"p = {cp['p']:.2e}",
                "",
                f"**Cluster bootstrap** (n_tasks={cb['n_tasks']}): "
                f"mean(A−B) = {cb['mean_diff']*100:+.1f} pp, 95% CI [{cb['ci_lo']*100:+.1f}, {cb['ci_hi']*100:+.1f}]",
                "",
            ]

    tag = f"_{args.tag}" if args.tag else ""
    out = ROOT / "benchmark" / f"clustered_stats{tag}.md"
    out.write_text("\n".join(md))
    print("\n".join(md))
    print(f"\nsaved → {out}")


if __name__ == "__main__":
    main()
