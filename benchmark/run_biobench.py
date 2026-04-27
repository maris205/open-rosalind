"""Run the Open-Rosalind Mini BioBench v0.

Usage:
    # 1. start the server first:
    python -m open_rosalind.cli serve --port 6006 &

    # 2. run the bench:
    python benchmark/run_biobench.py \
        --tasks benchmark/biobench_v0.jsonl \
        --base-url http://127.0.0.1:6006 \
        --out benchmark/results.json

The bench scores four metrics per task:
    - skill_correct       : agent picked the right top-level skill
    - tool_called         : every expected tool was actually invoked
    - has_trace           : trace_steps is non-empty
    - has_evidence        : evidence has at least one non-empty field
    - check_passed        : per-task semantic check (configurable per task)

Final accuracy = mean(check_passed). The other rates are reported alongside
to help diagnose failure modes (wrong routing vs. wrong evidence vs. flaky
LLM summary).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests


def get_path(obj: Any, path: str) -> Any:
    """Walk a dotted path. Each segment is either a key or an integer index."""
    cur = obj
    for seg in path.split("."):
        if cur is None:
            return None
        if isinstance(cur, list):
            try:
                cur = cur[int(seg)]
            except (ValueError, IndexError):
                return None
        elif isinstance(cur, dict):
            cur = cur.get(seg)
        else:
            return None
    return cur


def evaluate_check(check: dict, response: dict) -> tuple[bool, str]:
    """Return (passed, reason). `check` is the per-task `expected.checks` dict."""
    if not check:
        return True, "no check"
    ci = bool(check.get("case_insensitive"))

    def norm(x):
        if isinstance(x, str) and ci:
            return x.lower()
        return x

    if "evidence_path" in check:
        val = get_path(response.get("evidence"), check["evidence_path"])
    elif "annotation_path" in check:
        val = get_path(response.get("annotation"), check["annotation_path"])
    elif "summary_contains" in check:
        val = response.get("summary") or ""
    else:
        return False, f"unknown check shape: {check}"

    if "equals" in check:
        ok = norm(val) == norm(check["equals"])
        return ok, f"got={val!r} expected={check['equals']!r}"
    if "approx" in check:
        try:
            tol = float(check.get("tol", 0.1))
            ok = abs(float(val) - float(check["approx"])) <= tol
        except (TypeError, ValueError):
            ok = False
        return ok, f"got={val!r} approx={check['approx']} tol={check.get('tol',0.1)}"
    if "starts_with" in check:
        ok = isinstance(val, str) and norm(val).startswith(norm(check["starts_with"]))
        return ok, f"got={val!r} starts_with={check['starts_with']!r}"
    if "contains" in check:
        ok = isinstance(val, str) and norm(check["contains"]) in norm(val)
        return ok, f"got={val!r} contains={check['contains']!r}"
    if "contains_any" in check:
        if isinstance(val, list):
            ok = any(any(norm(x) == norm(item) for item in val) for x in check["contains_any"])
        else:
            ok = isinstance(val, str) and any(norm(x) in norm(val) for x in check["contains_any"])
        return ok, f"got={val!r} contains_any={check['contains_any']!r}"
    if "min" in check:
        try:
            ok = float(val) >= float(check["min"])
        except (TypeError, ValueError):
            ok = False
        return ok, f"got={val!r} min={check['min']}"
    if "summary_contains" in check:
        s = norm(val)
        ok = all(norm(t) in s for t in check["summary_contains"])
        return ok, f"summary_len={len(val)} needs={check['summary_contains']}"
    return False, f"unhandled check {check}"


def evaluate_task(task: dict, response: dict) -> dict:
    exp = task["expected"]
    skill_correct = response.get("skill") == exp.get("skill")

    tool_names = [s.get("skill") for s in (response.get("trace_steps") or [])]
    expected_tools = exp.get("tool_called", [])
    tool_called = all(t in tool_names for t in expected_tools) if expected_tools else True

    has_trace = bool(response.get("trace_steps"))
    ev = response.get("evidence") or {}
    has_evidence = any(v for k, v in ev.items() if k != "annotation" and v)

    check_passed, check_reason = evaluate_check(exp.get("checks", {}), response)

    return {
        "id": task["id"],
        "category": task.get("category"),
        "skill_correct": skill_correct,
        "skill_got": response.get("skill"),
        "skill_expected": exp.get("skill"),
        "tool_called": tool_called,
        "tools_got": tool_names,
        "tools_expected": expected_tools,
        "has_trace": has_trace,
        "has_evidence": has_evidence,
        "check_passed": check_passed,
        "check_reason": check_reason,
        "confidence": response.get("confidence"),
        "session_id": response.get("session_id"),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tasks", default="benchmark/biobench_v0.jsonl")
    p.add_argument("--base-url", default="http://127.0.0.1:6006")
    p.add_argument("--out", default="benchmark/results.json")
    p.add_argument("--summary", default="benchmark/results.md")
    p.add_argument("--timeout", type=int, default=180)
    args = p.parse_args()

    tasks = [json.loads(line) for line in Path(args.tasks).read_text().splitlines() if line.strip()]
    rows = []
    print(f"running {len(tasks)} tasks against {args.base_url}", file=sys.stderr)

    for i, task in enumerate(tasks, 1):
        body = {"input": task["input"], "mode": task.get("mode", "auto")}
        t0 = time.time()
        try:
            r = requests.post(f"{args.base_url}/api/analyze", json=body, timeout=args.timeout)
            r.raise_for_status()
            resp = r.json()
        except Exception as e:
            resp = {"error": f"{type(e).__name__}: {e}"}
        dt = time.time() - t0
        if "error" in resp and "skill" not in resp:
            row = {"id": task["id"], "category": task.get("category"),
                   "skill_correct": False, "tool_called": False,
                   "has_trace": False, "has_evidence": False,
                   "check_passed": False, "check_reason": resp["error"],
                   "elapsed_s": round(dt, 2)}
        else:
            row = evaluate_task(task, resp)
            row["elapsed_s"] = round(dt, 2)
        rows.append(row)
        mark = "✓" if row["check_passed"] else "✗"
        print(f"  [{i:02d}/{len(tasks)}] {mark} {task['id']:<8} {row.get('check_reason','')[:80]}", file=sys.stderr)

    metrics = aggregate(rows)
    out = {"meta": {"base_url": args.base_url, "n_tasks": len(rows)}, "metrics": metrics, "rows": rows}
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False))
    Path(args.summary).write_text(render_summary(metrics, rows))
    print(f"\nwrote {args.out} and {args.summary}", file=sys.stderr)
    print_metrics(metrics)


def aggregate(rows: list[dict]) -> dict:
    n = len(rows)
    by_cat: dict[str, list[dict]] = {}
    for r in rows:
        by_cat.setdefault(r.get("category") or "other", []).append(r)

    def rate(rs, key):
        return round(sum(1 for r in rs if r.get(key)) / max(len(rs), 1), 3)

    out = {
        "n_tasks": n,
        "accuracy": rate(rows, "check_passed"),
        "skill_correct_rate": rate(rows, "skill_correct"),
        "tool_called_rate": rate(rows, "tool_called"),
        "has_trace_rate": rate(rows, "has_trace"),
        "has_evidence_rate": rate(rows, "has_evidence"),
        "by_category": {
            cat: {
                "n": len(rs),
                "accuracy": rate(rs, "check_passed"),
                "skill_correct_rate": rate(rs, "skill_correct"),
                "tool_called_rate": rate(rs, "tool_called"),
            }
            for cat, rs in by_cat.items()
        },
    }
    return out


def render_summary(metrics: dict, rows: list[dict]) -> str:
    lines = ["# Mini BioBench v0 — Results\n"]
    lines.append(f"- Tasks: **{metrics['n_tasks']}**")
    lines.append(f"- Accuracy (semantic check): **{metrics['accuracy']:.1%}**")
    lines.append(f"- Skill routed correctly:    **{metrics['skill_correct_rate']:.1%}**")
    lines.append(f"- Expected tools called:     **{metrics['tool_called_rate']:.1%}**")
    lines.append(f"- Has trace:                 **{metrics['has_trace_rate']:.1%}**")
    lines.append(f"- Has evidence:              **{metrics['has_evidence_rate']:.1%}**\n")
    lines.append("## By category\n")
    lines.append("| Category | n | Accuracy | Skill correct | Tool called |")
    lines.append("|---|---|---|---|---|")
    for cat, m in metrics["by_category"].items():
        lines.append(f"| {cat} | {m['n']} | {m['accuracy']:.0%} | {m['skill_correct_rate']:.0%} | {m['tool_called_rate']:.0%} |")
    lines.append("\n## Per-task results\n")
    lines.append("| ID | Cat | Pass | Skill ok | Tool ok | Conf | Reason |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in rows:
        mark = "✅" if r["check_passed"] else "❌"
        sk = "✓" if r.get("skill_correct") else "✗"
        to = "✓" if r.get("tool_called") else "✗"
        c = r.get("confidence")
        c_s = f"{c:.2f}" if isinstance(c, (int, float)) else "—"
        reason = (r.get("check_reason") or "").replace("|", "\\|")[:80]
        lines.append(f"| `{r['id']}` | {r.get('category','?')} | {mark} | {sk} | {to} | {c_s} | {reason} |")
    return "\n".join(lines) + "\n"


def print_metrics(m: dict):
    print(f"\n=== Mini BioBench v0 ({m['n_tasks']} tasks) ===")
    print(f"Accuracy:           {m['accuracy']:.1%}")
    print(f"Skill correct:      {m['skill_correct_rate']:.1%}")
    print(f"Tool called:        {m['tool_called_rate']:.1%}")
    print(f"Has trace:          {m['has_trace_rate']:.1%}")
    print(f"Has evidence:       {m['has_evidence_rate']:.1%}")
    print()
    for cat, mm in m["by_category"].items():
        print(f"  {cat:12s} n={mm['n']:2d}  acc={mm['accuracy']:.0%}  skill={mm['skill_correct_rate']:.0%}  tool={mm['tool_called_rate']:.0%}")


if __name__ == "__main__":
    main()
