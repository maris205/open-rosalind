"""Redis/RQ queue integration for persistent Agent tasks."""

from __future__ import annotations

import os
import uuid

from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

try:
    from .database import get_task_plan
except ImportError:
    from database import get_task_plan  # type: ignore[no-redef]


REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
QUEUE_NAME = os.environ.get("ROSALIND_QUEUE", "rosalind")
redis_connection = Redis.from_url(REDIS_URL)
task_queue = Queue(QUEUE_NAME, connection=redis_connection, default_timeout=900)


def enqueue_plan_task(user_id: str, plan_id: str, mode: str) -> dict[str, object]:
    if mode not in {"next", "all"}:
        raise ValueError("不支持的任务执行模式。")
    job_id = uuid.uuid4().hex
    lock_key = f"rosalind:plan-lock:{plan_id}"
    if not redis_connection.set(lock_key, job_id, nx=True, ex=1800):
        raise ValueError("该计划已有后台任务正在排队或执行。")
    try:
        job = task_queue.enqueue(
            "web_app.worker_tasks.execute_plan_task",
            user_id,
            plan_id,
            mode,
            job_id=job_id,
            job_timeout=900,
            result_ttl=24 * 60 * 60,
            failure_ttl=7 * 24 * 60 * 60,
            meta={"user_id": user_id, "plan_id": plan_id, "mode": mode},
        )
    except Exception:
        redis_connection.delete(lock_key)
        raise
    return {"jobId": job.id, "status": job.get_status(refresh=True), "planId": plan_id, "mode": mode}


def release_plan_lock(plan_id: str, job_id: str = "", force: bool = False) -> None:
    lock_key = f"rosalind:plan-lock:{plan_id}"
    value = redis_connection.get(lock_key)
    if value and (force or value.decode("utf-8") == job_id):
        redis_connection.delete(lock_key)


def get_queue_job(user_id: str, job_id: str) -> dict[str, object] | None:
    try:
        job = Job.fetch(job_id, connection=redis_connection)
    except NoSuchJobError:
        return None
    if job.meta.get("user_id") != user_id:
        return None
    plan_id = str(job.meta.get("plan_id", ""))
    return {
        "jobId": job.id,
        "status": job.get_status(refresh=True),
        "planId": plan_id,
        "mode": job.meta.get("mode"),
        "error": job.exc_info[-4000:] if job.exc_info else "",
        "plan": get_task_plan(user_id, plan_id) if plan_id else None,
    }


def queue_health() -> dict[str, object]:
    redis_connection.ping()
    return {
        "ok": True,
        "queue": QUEUE_NAME,
        "queued": len(task_queue),
        "redis": "ready",
    }
