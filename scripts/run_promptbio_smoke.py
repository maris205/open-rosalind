#!/usr/bin/env python3
"""Run a lightweight PromptBio-Bench subset through Rosalind OpenHands."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web_app.openhands_runtime import execute_step  # noqa: E402


TASKS_ROOT = Path(os.environ.get("PROMPTBIO_TASKS_ROOT", "/root/promptbio-bench-data/tasks"))
EVALUATOR_ROOT = Path(os.environ.get("PROMPTBIO_EVALUATOR_ROOT", "/root/promptbio-bench"))
WORKSPACE_ROOT = ROOT / "data" / "openhands-workspace" / "project" / "promptbio"
CONTAINER_WORKSPACE_ROOT = Path("/workspace/project")
RESULTS_ROOT = ROOT / "data" / "promptbio-results"
RUN_LABEL = "rosalind_openhands"
CONTAINER_UID = 10001
CONTAINER_GID = 10001

DEFAULT_TASK_IDS = [
    "a-1-1",
    "a-3-10",
    "a-1-9",
    "a-1-7",
    "a-1-12",
    "a-14-5",
    "a-13-5",
    "a-7-4",
    "b-11-1",
    "b-5-8",
    "b-10-8",
    "b-4-7",
    "b-4-10",
    "b-4-4",
    "b-4-9",
    "a-10-1",
    "b-2-15",
    "a-3-15",
    "a-15-5",
    "a-10-3",
]


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def chown_tree(path: Path) -> None:
    os.chown(path, CONTAINER_UID, CONTAINER_GID)
    for child in path.rglob("*"):
        os.chown(child, CONTAINER_UID, CONTAINER_GID)


def stage_task(task_id: str, task: dict[str, object]) -> tuple[Path, Path]:
    task_source = TASKS_ROOT / task_id
    host_run_dir = WORKSPACE_ROOT / task_id / "rosalind_run1"
    container_run_dir = CONTAINER_WORKSPACE_ROOT
    host_run_dir.mkdir(parents=True, exist_ok=True)
    host_run_dir.chmod(0o750)

    for relative in task.get("input_files", []):
        source = task_source / str(relative)
        destination = host_run_dir / str(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(source, destination)

    chown_tree(host_run_dir)
    return host_run_dir, container_run_dir


def expected_outputs(task: dict[str, object]) -> list[dict[str, str]]:
    outputs: list[dict[str, str]] = []
    for raw in task.get("expected_output", []):
        if isinstance(raw, dict):
            outputs.append({
                "file": str(raw.get("file", "")),
                "type": str(raw.get("type", "")),
                "description": str(raw.get("description", "")),
            })
    return outputs


def output_files_exist(run_dir: Path, outputs: list[dict[str, str]]) -> bool:
    return bool(outputs) and all(list(run_dir.glob(item["file"])) for item in outputs)


def run_agent(task_id: str, task: dict[str, object], run_dir: Path, container_run_dir: Path) -> dict[str, object]:
    outputs = expected_outputs(task)
    if output_files_exist(run_dir, outputs):
        return {"ok": True, "reused": True, "content": "Existing output files reused.", "conversationId": ""}

    input_lines = [f"- {container_run_dir / str(item)}" for item in task.get("input_files", [])]
    output_lines = [
        f"- {container_run_dir / item['file']} (type={item['type']}; {item['description']})"
        for item in outputs
    ]
    system_prompt = (
        "You are Rosalind Agent executing one PromptBio-Bench task inside OpenHands. "
        "Act immediately and keep the trajectory short enough to finish within 100 seconds. "
        "Use terminal or file tools to create every requested output file; a chat-only answer is a failure. "
        "Work only in the assigned task directory. Do not inspect other task directories, reference answers, "
        "or reference scripts. Prefer a single auditable Python script using standard libraries when possible. "
        "Verify output existence and basic validity before finishing."
    )
    task_prompt = "\n".join([
        f"Task ID: {task_id}",
        f"Working directory: {container_run_dir}",
        "",
        "Question:",
        str(task.get("question", "")),
        "",
        "Input files:",
        *(input_lines or ["- none"]),
        "",
        "Required output files (names and locations must match):",
        *output_lines,
        "",
        "Do not stop after proposing code. Execute it and leave the final files in the working directory.",
    ])
    return execute_step(system_prompt, task_prompt, workspace_path=run_dir)


def evaluator_environment() -> dict[str, str]:
    env = os.environ.copy()
    api_key = env.get("DASHSCOPE_API_KEY") or env.get("OPENAI_API_KEY", "")
    base_url = env.get("QWEN_BASE_URL") or env.get("OPENAI_BASE_URL", "")
    env.update({
        "OPENAI_API_KEY": api_key,
        "OPENAI_BASE_URL": base_url,
        "OPENAI_API_BASE": base_url,
        "OPENAI_DISABLE_THINKING": "1",
    })
    return env


def run_evaluator(task_id: str, run_dir: Path) -> dict[str, object]:
    output_dir = RESULTS_ROOT / task_id
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        str(EVALUATOR_ROOT / ".venv" / "bin" / "python"),
        str(EVALUATOR_ROOT / "run_eval.py"),
        "--task-dir", str(TASKS_ROOT / task_id),
        "--result-dir", str(run_dir),
        "--output-dir", str(output_dir),
        "--label", RUN_LABEL,
        "--model", "openai:qwen3.7-max",
    ]
    completed = subprocess.run(
        command,
        cwd=EVALUATOR_ROOT,
        env=evaluator_environment(),
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    result_path = output_dir / f"{task_id}_{RUN_LABEL}.json"
    result = load_json(result_path) if result_path.exists() else {}
    result.update({
        "evaluator_exit_code": completed.returncode,
        "evaluator_stdout_tail": completed.stdout[-4000:],
        "evaluator_stderr_tail": completed.stderr[-2000:],
    })
    return result


def save_summary(rows: list[dict[str, object]]) -> None:
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    summary_path = RESULTS_ROOT / "smoke20_summary.json"
    summary_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    scored = [row for row in rows if isinstance(row.get("score"), (int, float))]
    average = sum(float(row["score"]) for row in scored) / len(scored) if scored else None
    lines = [
        "# PromptBio-Bench Rosalind Smoke 20",
        "",
        f"- Completed records: {len(rows)}",
        f"- Scored tasks: {len(scored)}",
        f"- Average similarity: {average:.4f}" if average is not None else "- Average similarity: unavailable",
        "",
        "| Task | Agent | Score | Seconds | Note |",
        "|---|---|---:|---:|---|",
    ]
    for row in rows:
        score = row.get("score")
        score_text = f"{float(score):.4f}" if isinstance(score, (int, float)) else "-"
        lines.append(
            f"| {row['task_id']} | {row['agent_status']} | {score_text} | "
            f"{float(row['duration_seconds']):.1f} | {str(row.get('note', '')).replace('|', '/')} |"
        )
    (RESULTS_ROOT / "smoke20_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_task(task_id: str) -> dict[str, object]:
    task_path = TASKS_ROOT / task_id / "task.json"
    if not task_path.exists():
        raise FileNotFoundError(f"PromptBio task not found: {task_id}")
    task = load_json(task_path)
    run_dir, container_run_dir = stage_task(task_id, task)
    started = time.monotonic()
    try:
        agent = run_agent(task_id, task, run_dir, container_run_dir)
        agent_status = "reused" if agent.get("reused") else "completed"
        response = str(agent.get("content", ""))
    except Exception as exc:  # noqa: BLE001 - benchmark should continue after one failed task
        response = str(exc)
        if output_files_exist(run_dir, expected_outputs(task)):
            timed_out = "timed out" in response.lower() or "HTTP 504" in response
            agent_status = "timed_out_with_outputs" if timed_out else "failed_with_outputs"
        else:
            agent_status = "failed"

    output_dir = RESULTS_ROOT / task_id
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "agent_response.md").write_text(response + "\n", encoding="utf-8")

    score = None
    note = ""
    evaluator: dict[str, object] = {}
    if output_files_exist(run_dir, expected_outputs(task)):
        try:
            evaluator = run_evaluator(task_id, run_dir)
            score = evaluator.get("avg_similarity")
            note = str(evaluator.get("error") or "")
        except Exception as exc:  # noqa: BLE001
            note = f"Evaluator failed: {exc}"
    else:
        note = "Required output file missing."

    return {
        "task_id": task_id,
        "question": task.get("question", ""),
        "agent_status": agent_status,
        "score": score,
        "duration_seconds": time.monotonic() - started,
        "note": note,
        "evaluator_exit_code": evaluator.get("evaluator_exit_code"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", action="append", dest="tasks", help="Task ID; may be repeated")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N selected tasks")
    args = parser.parse_args()
    task_ids = args.tasks or DEFAULT_TASK_IDS
    if args.limit is not None:
        task_ids = task_ids[: args.limit]

    rows: list[dict[str, object]] = []
    for index, task_id in enumerate(task_ids, start=1):
        print(f"[{index}/{len(task_ids)}] {task_id} starting", flush=True)
        row = run_task(task_id)
        rows.append(row)
        save_summary(rows)
        print(
            f"[{index}/{len(task_ids)}] {task_id} agent={row['agent_status']} "
            f"score={row['score']} seconds={row['duration_seconds']:.1f} note={row['note']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
