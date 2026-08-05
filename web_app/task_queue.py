"""Redis/RQ queue integration for persistent Agent tasks."""

from __future__ import annotations

import os
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor

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
TASK_TIMEOUT_SECONDS = int(os.environ.get("ROSALIND_TASK_TIMEOUT", "3600"))
DESKTOP_MODE = os.environ.get("ROSALIND_DESKTOP_MODE", "0") == "1"
redis_connection = Redis.from_url(REDIS_URL)
task_queue = Queue(QUEUE_NAME, connection=redis_connection, default_timeout=TASK_TIMEOUT_SECONDS)
LOCAL_EXECUTOR = ThreadPoolExecutor(max_workers=int(os.environ.get("ROSALIND_DESKTOP_CONCURRENCY", "1")), thread_name_prefix="rosalind-agent")
LOCAL_JOBS: dict[str, dict[str, object]] = {}
LOCAL_PLAN_LOCKS: dict[str, str] = {}
LOCAL_JOBS_LOCK = threading.Lock()

_RELEASE_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
end
return 0
"""


def _execute_local_job(job_id: str) -> None:
    with LOCAL_JOBS_LOCK:
        job = LOCAL_JOBS[job_id]
        job["status"] = "started"
    try:
        from .server import run_all_task_steps, run_next_task_step

        result = run_next_task_step(str(job["user_id"]), str(job["plan_id"])) if job["mode"] == "next" else run_all_task_steps(str(job["user_id"]), str(job["plan_id"]))
        with LOCAL_JOBS_LOCK:
            job["result"] = result
            job["status"] = "finished"
    except Exception:  # noqa: BLE001 - preserve a bounded task error for status polling
        with LOCAL_JOBS_LOCK:
            job["error"] = traceback.format_exc()[-4000:]
            job["status"] = "failed"
    finally:
        release_plan_lock(str(job["plan_id"]), job_id)


def enqueue_plan_task(user_id: str, plan_id: str, mode: str) -> dict[str, object]:
    if mode not in {"next", "all"}:
        raise ValueError("不支持的任务执行模式。")
    job_id = uuid.uuid4().hex
    if DESKTOP_MODE:
        with LOCAL_JOBS_LOCK:
            if plan_id in LOCAL_PLAN_LOCKS:
                raise ValueError("该计划已有后台任务正在排队或执行。")
            LOCAL_PLAN_LOCKS[plan_id] = job_id
            LOCAL_JOBS[job_id] = {
                "job_id": job_id,
                "user_id": user_id,
                "plan_id": plan_id,
                "mode": mode,
                "status": "queued",
                "error": "",
            }
        LOCAL_EXECUTOR.submit(_execute_local_job, job_id)
        return {"jobId": job_id, "status": "queued", "planId": plan_id, "mode": mode}
    lock_key = f"rosalind:plan-lock:{plan_id}"
    if not redis_connection.set(lock_key, job_id, nx=True, ex=TASK_TIMEOUT_SECONDS + 600):
        raise ValueError("该计划已有后台任务正在排队或执行。")
    try:
        job = task_queue.enqueue(
            "web_app.worker_tasks.execute_plan_task",
            user_id,
            plan_id,
            mode,
            job_id=job_id,
            job_timeout=TASK_TIMEOUT_SECONDS,
            result_ttl=24 * 60 * 60,
            failure_ttl=7 * 24 * 60 * 60,
            meta={"user_id": user_id, "plan_id": plan_id, "mode": mode},
        )
    except Exception:
        redis_connection.delete(lock_key)
        raise
    return {"jobId": job.id, "status": job.get_status(refresh=True), "planId": plan_id, "mode": mode}


def release_plan_lock(plan_id: str, job_id: str = "", force: bool = False) -> None:
    if DESKTOP_MODE:
        with LOCAL_JOBS_LOCK:
            if force or LOCAL_PLAN_LOCKS.get(plan_id) == job_id:
                LOCAL_PLAN_LOCKS.pop(plan_id, None)
        return
    lock_key = f"rosalind:plan-lock:{plan_id}"
    if force:
        redis_connection.delete(lock_key)
        return
    if job_id:
        redis_connection.eval(_RELEASE_LOCK_SCRIPT, 1, lock_key, job_id)


def get_queue_job(user_id: str, job_id: str) -> dict[str, object] | None:
    if DESKTOP_MODE:
        with LOCAL_JOBS_LOCK:
            job = dict(LOCAL_JOBS.get(job_id) or {})
        if not job or job.get("user_id") != user_id:
            return None
        plan_id = str(job.get("plan_id", ""))
        return {
            "jobId": job_id,
            "status": job.get("status"),
            "planId": plan_id,
            "mode": job.get("mode"),
            "error": job.get("error", ""),
            "plan": get_task_plan(user_id, plan_id) if plan_id else None,
        }
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
    if DESKTOP_MODE:
        with LOCAL_JOBS_LOCK:
            active = sum(1 for job in LOCAL_JOBS.values() if job.get("status") in {"queued", "started"})
        return {
            "ok": True,
            "queue": "local-desktop",
            "queued": active,
            "redis": "not-required",
        }
    redis_connection.ping()
    return {
        "ok": True,
        "queue": QUEUE_NAME,
        "queued": len(task_queue),
        "redis": "ready",
    }
