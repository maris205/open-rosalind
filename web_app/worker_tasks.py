"""Functions executed by the Open-Rosalind RQ worker."""

from __future__ import annotations


def execute_plan_task(user_id: str, plan_id: str, mode: str) -> dict[str, object]:
    # Import lazily so RQ starts quickly and each workhorse gets fresh configuration.
    from rq import get_current_job

    from .server import run_all_task_steps, run_next_task_step
    from .task_queue import release_plan_lock

    job = get_current_job()
    try:
        if mode == "next":
            return run_next_task_step(user_id, plan_id)
        if mode == "all":
            return run_all_task_steps(user_id, plan_id)
        raise ValueError(f"Unsupported plan execution mode: {mode}")
    finally:
        release_plan_lock(plan_id, job.id if job else "")
