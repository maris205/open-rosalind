import unittest
from unittest.mock import patch

from web_app import task_queue


class DesktopQueueTests(unittest.TestCase):
    def tearDown(self) -> None:
        with task_queue.LOCAL_JOBS_LOCK:
            task_queue.LOCAL_JOBS.clear()
            task_queue.LOCAL_PLAN_LOCKS.clear()

    def test_desktop_queue_does_not_require_redis(self) -> None:
        submitted = []
        with (
            patch.object(task_queue, "DESKTOP_MODE", True),
            patch.object(task_queue.LOCAL_EXECUTOR, "submit", side_effect=lambda function, job_id: submitted.append((function, job_id))),
            patch.object(task_queue, "get_task_plan", return_value={"id": "plan-1", "status": "running"}),
        ):
            queued = task_queue.enqueue_plan_task("user-1", "plan-1", "all")
            status = task_queue.get_queue_job("user-1", str(queued["jobId"]))
            health = task_queue.queue_health()

            self.assertEqual(queued["status"], "queued")
            self.assertEqual(status["status"], "queued")
            self.assertEqual(status["plan"]["id"], "plan-1")
            self.assertEqual(health["redis"], "not-required")
            self.assertEqual(len(submitted), 1)

            task_queue.release_plan_lock("plan-1", str(queued["jobId"]))
            self.assertNotIn("plan-1", task_queue.LOCAL_PLAN_LOCKS)

    def test_desktop_queue_prevents_duplicate_plan_execution(self) -> None:
        with (
            patch.object(task_queue, "DESKTOP_MODE", True),
            patch.object(task_queue.LOCAL_EXECUTOR, "submit", return_value=None),
        ):
            task_queue.enqueue_plan_task("user-1", "plan-1", "all")
            with self.assertRaisesRegex(ValueError, "已有后台任务"):
                task_queue.enqueue_plan_task("user-1", "plan-1", "all")


if __name__ == "__main__":
    unittest.main()
