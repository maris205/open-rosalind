"""Run BioBench v0.3 (harness tasks) against Open-Rosalind MVP3.

Usage:
    python benchmark/run_biobench_v03.py --version mvp3-baseline
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import requests


def run_harness_task(base_url: str, task: dict) -> dict:
    """Run one harness task via CLI and collect results."""
    task_id = f"bench_{task['id']}_{int(time.time())}"

    # Run task via CLI
    cmd = [
        sys.executable, "-m", "open_rosalind.cli",
        "task", "run", task["input"],
        "--max-steps", str(task.get("max_steps", 5)),
        "--json"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return {"error": f"CLI failed: {result.stderr}", "task_id": task_id}

        task_result = json.loads(result.stdout)
        return task_result
    except subprocess.TimeoutExpired:
        return {"error": "Timeout", "task_id": task_id}
    except Exception as e:
        return {"error": str(e), "task_id": task_id}


def evaluate_harness_task(task: dict, result: dict) -> tuple[bool, str]:
    """Evaluate harness task result."""
    if "error" in result:
        return False, f"error: {result['error']}"

    checks = task.get("checks", {})

    # Check task status
    if checks.get("task_status") and result.get("status") != checks["task_status"]:
        return False, f"status={result.get('status')} expected={checks['task_status']}"

    # Check min steps
    if checks.get("min_steps"):
        n_steps = len(result.get("steps", []))
        if n_steps < checks["min_steps"]:
            return False, f"steps={n_steps} min={checks['min_steps']}"

    # Check evidence pool
    if checks.get("evidence_pool_min"):
        n_evidence = result.get("state", {}).get("n_evidence", 0)
        if n_evidence < checks["evidence_pool_min"]:
            return False, f"evidence={n_evidence} min={checks['evidence_pool_min']}"

    # Check keywords (in final report or step summaries)
    if task.get("expected_keywords"):
        text = result.get("final_report", "").lower()
        for kw in task["expected_keywords"]:
            if kw.lower() not in text:
                return False, f"missing keyword: {kw}"

    return True, "ok"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tasks", default="benchmark/biobench_v03.jsonl")
    p.add_argument("--base-url", default="http://127.0.0.1:6006")
    p.add_argument("--version", default="v0.3")
    p.add_argument("--out", default="benchmark/results_v03.json")
    p.add_argument("--summary", default="benchmark/results_v03.md")
    p.add_argument("--history", default="benchmark/history_v03.jsonl")
    args = p.parse_args()

    tasks = [json.loads(line) for line in Path(args.tasks).read_text().splitlines() if line.strip()]

    print(f"running {len(tasks)} harness tasks (version={args.version})")

    results = []
    passed = 0

    for i, task in enumerate(tasks, 1):
        result = run_harness_task(args.base_url, task)
        ok, msg = evaluate_harness_task(task, result)

        icon = "✅" if ok else "❌"
        print(f"  [{i:02d}/{len(tasks):02d}] {icon} {task['id']:20s} {msg}")

        results.append({
            "task": task,
            "result": result,
            "passed": ok,
            "message": msg,
        })

        if ok:
            passed += 1

    # Compute metrics
    task_accuracy = passed / len(tasks) if tasks else 0.0
    task_completion_rate = sum(1 for r in results if r["result"].get("status") == "completed") / len(tasks)
    workflow_success_rate = sum(
        1 for r in results
        if r["result"].get("status") == "completed"
        and all(s.get("status") == "success" for s in r["result"].get("steps", []))
    ) / len(tasks)
    evidence_aggregation_rate = sum(
        1 for r in results
        if r["result"].get("state", {}).get("n_evidence", 0) > 0
    ) / len(tasks)

    metrics = {
        "task_accuracy": task_accuracy,
        "task_completion_rate": task_completion_rate,
        "workflow_success_rate": workflow_success_rate,
        "evidence_aggregation_rate": evidence_aggregation_rate,
    }

    # Write results
    Path(args.out).write_text(json.dumps({"results": results, "metrics": metrics}, indent=2))

    # Write summary
    summary = f"""# BioBench v0.3 Results ({args.version})

## Metrics
- Task accuracy: {task_accuracy:.1%}
- Task completion rate: {task_completion_rate:.1%}
- Workflow success rate: {workflow_success_rate:.1%}
- Evidence aggregation rate: {evidence_aggregation_rate:.1%}

## Tasks
"""
    for r in results:
        icon = "✅" if r["passed"] else "❌"
        summary += f"{icon} {r['task']['id']}: {r['message']}\n"

    Path(args.summary).write_text(summary)

    # Append to history
    history_entry = {
        "version": args.version,
        "n_tasks": len(tasks),
        "metrics": metrics,
    }
    with Path(args.history).open("a") as f:
        f.write(json.dumps(history_entry) + "\n")

    print(f"\n=== BioBench v0.3 {args.version} ({len(tasks)} tasks) ===")
    print(f"Task accuracy:        {task_accuracy:.1%}")
    print(f"Task completion:      {task_completion_rate:.1%}")
    print(f"Workflow success:     {workflow_success_rate:.1%}")
    print(f"Evidence aggregation: {evidence_aggregation_rate:.1%}")


if __name__ == "__main__":
    main()
