"""Open-Rosalind Mini BioBench — gpt4.md scoring rubric.

Five standard metrics (one row per Open-Rosalind version):

    Task accuracy       — strict per-task pass/fail (skill + tool + check + keywords)
    Tool correctness    — every expected tool was actually invoked
    Evidence rate       — `evidence` is non-empty AND `must_have_evidence` task was satisfied
    Trace completeness  — `trace_steps` is non-empty AND `must_have_trace` task was satisfied
    Failure rate        — task hit a hard error (HTTP 5xx, exception, or trace says all tools errored)

Usage:
    python -m open_rosalind.cli serve --port 6006 &
    python benchmark/run_biobench.py \
        --tasks benchmark/biobench_v0.jsonl \
        --version v0.1 \
        --base-url http://127.0.0.1:6006 \
        --out benchmark/results.json \
        --summary benchmark/results.md \
        --history benchmark/history.jsonl

Each run appends one row to history.jsonl, which BENCHMARK.md reads to
produce a version-comparison table.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


def get_path(obj: Any, path: str) -> Any:
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
    if not check:
        return True, "no check"
    ci = bool(check.get("case_insensitive"))

    def norm(x):
        return x.lower() if isinstance(x, str) and ci else x

    if "evidence_path" in check:
        val = get_path(response.get("evidence"), check["evidence_path"])
    elif "annotation_path" in check:
        val = get_path(response.get("annotation"), check["annotation_path"])
    elif "summary_contains" in check:
        val = response.get("summary") or ""
    else:
        return False, f"unknown check shape: {check}"

    if "equals" in check:
        return norm(val) == norm(check["equals"]), f"got={val!r} expected={check['equals']!r}"
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


def keyword_hits(response: dict, keywords: list[str]) -> tuple[int, int]:
    """Return (hit_count, total). A keyword hits if it appears (case-insensitive)
    in summary OR in any string field of evidence."""
    if not keywords:
        return 0, 0
    summary = (response.get("summary") or "").lower()
    ev_blob = json.dumps(response.get("evidence") or {}, ensure_ascii=False).lower()
    haystack = summary + "\n" + ev_blob
    hit = sum(1 for kw in keywords if kw.lower() in haystack)
    return hit, len(keywords)


def evaluate_task(task: dict, response: dict, error: str | None) -> dict:
    if error:
        return {
            "id": task["id"], "category": task.get("category"),
            "skill_correct": False, "tool_called": False,
            "evidence_ok": False, "trace_ok": False, "keyword_ok": False,
            "check_passed": False, "task_passed": False, "failed": True,
            "fail_reason": error,
            "skill_got": None, "skill_expected": task.get("expected_skill"),
            "tools_got": [], "tools_expected": task.get("expected_tools", []),
            "keyword_hit": 0, "keyword_total": len(task.get("expected_keywords", [])),
            "confidence": None, "session_id": None,
        }

    skill_correct = response.get("skill") == task.get("expected_skill")
    tool_names = [s.get("skill") for s in (response.get("trace_steps") or [])]
    expected_tools = task.get("expected_tools", [])
    tool_called = all(t in tool_names for t in expected_tools) if expected_tools else True

    has_trace = bool(response.get("trace_steps"))
    ev = response.get("evidence") or {}
    has_evidence = any(v for k, v in ev.items() if k not in ("annotation", "notes") and v)
    evidence_ok = has_evidence if task.get("must_have_evidence", True) else True
    trace_ok = has_trace if task.get("must_have_trace", True) else True

    check_passed, check_reason = evaluate_check(task.get("checks", {}), response)
    hit, total = keyword_hits(response, task.get("expected_keywords", []))
    keyword_ok = total == 0 or hit >= max(1, int(total * 0.6))  # ≥60% of keywords present

    task_passed = bool(skill_correct and tool_called and check_passed and keyword_ok and evidence_ok and trace_ok)

    return {
        "id": task["id"], "category": task.get("category"),
        "skill_correct": skill_correct, "skill_got": response.get("skill"),
        "skill_expected": task.get("expected_skill"),
        "tool_called": tool_called, "tools_got": tool_names,
        "tools_expected": expected_tools,
        "evidence_ok": evidence_ok, "trace_ok": trace_ok,
        "keyword_ok": keyword_ok, "keyword_hit": hit, "keyword_total": total,
        "check_passed": check_passed, "check_reason": check_reason,
        "task_passed": task_passed, "failed": False, "fail_reason": None,
        "confidence": response.get("confidence"),
        "session_id": response.get("session_id"),
    }


def aggregate(rows: list[dict]) -> dict:
    n = max(len(rows), 1)

    def rate(rs, key):
        rs2 = rs or rows
        return round(sum(1 for r in rs2 if r.get(key)) / max(len(rs2), 1), 4)

    by_cat: dict[str, list[dict]] = {}
    for r in rows:
        by_cat.setdefault(r.get("category") or "other", []).append(r)

    return {
        "n_tasks": len(rows),
        "task_accuracy": rate(rows, "task_passed"),
        "tool_correctness": rate(rows, "tool_called"),
        "evidence_rate": rate(rows, "evidence_ok"),
        "trace_completeness": rate(rows, "trace_ok"),
        "failure_rate": rate(rows, "failed"),
        "skill_correct_rate": rate(rows, "skill_correct"),
        "by_category": {
            cat: {
                "n": len(rs),
                "task_accuracy": rate(rs, "task_passed"),
                "tool_correctness": rate(rs, "tool_called"),
                "evidence_rate": rate(rs, "evidence_ok"),
                "trace_completeness": rate(rs, "trace_ok"),
                "failure_rate": rate(rs, "failed"),
            }
            for cat, rs in by_cat.items()
        },
    }


def render_markdown(meta: dict, metrics: dict, rows: list[dict]) -> str:
    L = []
    L.append(f"# Mini BioBench — {meta['version']} run\n")
    L.append(f"- Date: `{meta['date']}`")
    L.append(f"- Backend model: `{meta['model']}`")
    L.append(f"- Git SHA: `{meta['git_sha']}`")
    L.append(f"- Tasks: **{metrics['n_tasks']}**\n")

    L.append("## Headline metrics\n")
    L.append("| Metric | Value |")
    L.append("|---|---|")
    L.append(f"| Task accuracy        | **{metrics['task_accuracy']:.1%}** |")
    L.append(f"| Tool correctness     | **{metrics['tool_correctness']:.1%}** |")
    L.append(f"| Evidence rate        | **{metrics['evidence_rate']:.1%}** |")
    L.append(f"| Trace completeness   | **{metrics['trace_completeness']:.1%}** |")
    L.append(f"| Failure rate         | **{metrics['failure_rate']:.1%}** |\n")

    L.append("## By category\n")
    L.append("| Category | n | Task acc | Tool ok | Evidence | Trace | Failure |")
    L.append("|---|---|---|---|---|---|---|")
    for cat, m in metrics["by_category"].items():
        L.append(f"| {cat} | {m['n']} | {m['task_accuracy']:.0%} | {m['tool_correctness']:.0%} | "
                 f"{m['evidence_rate']:.0%} | {m['trace_completeness']:.0%} | {m['failure_rate']:.0%} |")
    L.append("")

    L.append("## Per-task detail\n")
    L.append("| ID | Category | Pass | Skill | Tool | KW | Check |")
    L.append("|---|---|---|---|---|---|---|")
    for r in rows:
        mark = "✅" if r.get("task_passed") else ("💥" if r.get("failed") else "❌")
        sk = "✓" if r.get("skill_correct") else "✗"
        to = "✓" if r.get("tool_called") else "✗"
        kw = f"{r.get('keyword_hit', 0)}/{r.get('keyword_total', 0)}"
        reason = (r.get("check_reason") or r.get("fail_reason") or "").replace("|", "\\|")[:80]
        L.append(f"| `{r['id']}` | {r.get('category', '?')} | {mark} | {sk} | {to} | {kw} | {reason} |")
    return "\n".join(L) + "\n"


def get_git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parent.parent, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tasks", default="benchmark/biobench_v0.jsonl")
    p.add_argument("--base-url", default="http://127.0.0.1:6006")
    p.add_argument("--version", default="v0.1")
    p.add_argument("--out", default="benchmark/results.json")
    p.add_argument("--summary", default="benchmark/results.md")
    p.add_argument("--history", default="benchmark/history.jsonl")
    p.add_argument("--timeout", type=int, default=180)
    args = p.parse_args()

    tasks = [json.loads(line) for line in Path(args.tasks).read_text().splitlines() if line.strip()]
    print(f"running {len(tasks)} tasks against {args.base_url} (version={args.version})", file=sys.stderr)

    health = requests.get(f"{args.base_url}/api/health", timeout=10).json()
    model = health.get("model", "unknown")

    rows = []
    t_start = time.time()
    for i, task in enumerate(tasks, 1):
        body = {"input": task["input"], "mode": task.get("mode", "auto")}
        t0 = time.time()
        err = None
        resp = {}
        try:
            r = requests.post(f"{args.base_url}/api/analyze", json=body, timeout=args.timeout)
            r.raise_for_status()
            resp = r.json()
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
        dt = time.time() - t0
        row = evaluate_task(task, resp, err)
        row["elapsed_s"] = round(dt, 2)
        rows.append(row)
        mark = "✅" if row["task_passed"] else ("💥" if row["failed"] else "❌")
        print(f"  [{i:02d}/{len(tasks)}] {mark} {task['id']:<8} {(row.get('check_reason') or row.get('fail_reason') or '')[:75]}",
              file=sys.stderr)
    elapsed = round(time.time() - t_start, 1)

    metrics = aggregate(rows)
    meta = {
        "version": args.version, "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": get_git_sha(), "model": model, "base_url": args.base_url,
        "tasks_file": args.tasks, "elapsed_s": elapsed,
    }
    out = {"meta": meta, "metrics": metrics, "rows": rows}
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False))
    Path(args.summary).write_text(render_markdown(meta, metrics, rows))

    history_line = json.dumps({"meta": meta, "metrics": {k: v for k, v in metrics.items() if k != "by_category"}})
    Path(args.history).touch(exist_ok=True)
    with Path(args.history).open("a") as f:
        f.write(history_line + "\n")

    print(f"\nwrote {args.out} / {args.summary} / appended {args.history}", file=sys.stderr)
    print()
    print(f"=== Mini BioBench {args.version} (model={model}, sha={meta['git_sha']}, {len(rows)} tasks, {elapsed}s) ===")
    print(f"Task accuracy:        {metrics['task_accuracy']:.1%}")
    print(f"Tool correctness:     {metrics['tool_correctness']:.1%}")
    print(f"Evidence rate:        {metrics['evidence_rate']:.1%}")
    print(f"Trace completeness:   {metrics['trace_completeness']:.1%}")
    print(f"Failure rate:         {metrics['failure_rate']:.1%}")


if __name__ == "__main__":
    main()
