"""Open-Rosalind background worker entry point."""

from __future__ import annotations

from rq import Queue, Worker

from .database import initialize_database, recover_interrupted_task_steps
from .task_queue import QUEUE_NAME, redis_connection, release_plan_lock


def main() -> int:
    initialize_database()
    recovered_plan_ids = recover_interrupted_task_steps()
    for plan_id in recovered_plan_ids:
        release_plan_lock(plan_id, force=True)
    if recovered_plan_ids:
        print(f"Recovered {len(recovered_plan_ids)} interrupted plan(s) as failed.")
    redis_connection.ping()
    queue = Queue(QUEUE_NAME, connection=redis_connection)
    worker = Worker([queue], connection=redis_connection, name="open-rosalind-worker")
    worker.work(with_scheduler=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
