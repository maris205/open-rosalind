import json
import os
import subprocess
import sys
import time
import unittest
from io import BytesIO

from web_app.desktop_agent_worker import (
    MAX_MESSAGE_BYTES,
    WorkerState,
    handle_request,
    serve,
)


class DesktopAgentWorkerTests(unittest.TestCase):
    def initialized_state(self) -> WorkerState:
        state = WorkerState()
        response = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"client": "test-suite", "protocolVersion": 2},
            },
            state,
        )
        self.assertEqual(response["result"]["protocolVersion"], 2)
        return state

    def test_oversized_message_fails_closed(self) -> None:
        output = BytesIO()

        status = serve(BytesIO(b"x" * (MAX_MESSAGE_BYTES + 1)), output)

        self.assertEqual(status, 1)
        response = json.loads(output.getvalue())
        self.assertEqual(response["error"]["code"], -32600)

    def test_requires_initialize_before_other_methods(self) -> None:
        response = handle_request(
            {"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}},
            WorkerState(),
        )

        self.assertEqual(response["error"]["code"], -32002)

    def test_stdio_protocol_initializes_pings_and_shuts_down(self) -> None:
        messages = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "client": "test-suite",
                    "protocolVersion": 2,
                },
            },
            {"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}},
            {"jsonrpc": "2.0", "id": 3, "method": "shutdown", "params": {}},
        ]
        payload = "".join(json.dumps(message) + "\n" for message in messages)
        environment = os.environ.copy()
        environment.pop("DASHSCOPE_API_KEY", None)
        process = subprocess.run(
            [sys.executable, "-m", "web_app.desktop_agent_worker"],
            input=payload,
            text=True,
            capture_output=True,
            timeout=3,
            check=False,
            env=environment,
        )

        self.assertEqual(process.returncode, 0, process.stderr)
        responses = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual([response["id"] for response in responses], [1, 2, 3])
        self.assertEqual(responses[0]["result"]["protocolVersion"], 2)
        self.assertTrue(responses[0]["result"]["capabilities"]["jobControl"])
        self.assertFalse(responses[0]["result"]["capabilities"]["modelCredentials"])
        self.assertTrue(responses[1]["result"]["ok"])
        self.assertTrue(responses[2]["result"]["ok"])

    def test_job_completes_with_structured_progress(self) -> None:
        state = self.initialized_state()
        started = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "job.start",
                "params": {
                    "jobId": "job-complete",
                    "request": {"input": "Plan a safe lifecycle test"},
                },
            },
            state,
        )
        self.assertEqual(started["result"]["jobId"], "job-complete")
        self.assertEqual(started["result"]["status"], "running")

        snapshot = started
        for request_id in range(3, 30):
            snapshot = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "job.status",
                    "params": {"jobId": "job-complete"},
                },
                state,
            )
            if snapshot["result"]["status"] == "completed":
                break
            time.sleep(0.01)

        result = snapshot["result"]
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["result"]["mode"], "lifecycle-stub-v2")
        self.assertEqual(
            [event["sequence"] for event in result["progress"]],
            list(range(1, len(result["progress"]) + 1)),
        )
        self.assertEqual(result["progress"][-1]["kind"], "completed")

    def test_running_job_can_be_cancelled(self) -> None:
        state = self.initialized_state()
        handle_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "job.start",
                "params": {
                    "jobId": "job-cancel",
                    "request": {"input": "Cancel me", "lifecycleWorkUnits": 50},
                },
            },
            state,
        )
        cancelled = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "job.cancel",
                "params": {"jobId": "job-cancel"},
            },
            state,
        )
        self.assertTrue(cancelled["result"]["cancellationRequested"])

        snapshot = cancelled
        for request_id in range(4, 30):
            snapshot = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "job.status",
                    "params": {"jobId": "job-cancel"},
                },
                state,
            )
            if snapshot["result"]["status"] == "cancelled":
                break
            time.sleep(0.01)

        self.assertEqual(snapshot["result"]["status"], "cancelled")
        self.assertIsNotNone(snapshot["result"]["endedAt"])

    def test_job_start_rejects_embedded_secrets(self) -> None:
        state = self.initialized_state()
        response = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "job.start",
                "params": {
                    "jobId": "job-secret",
                    "request": {"provider": {"api_key": "must-not-pass"}},
                },
            },
            state,
        )

        self.assertEqual(response["error"]["code"], -32602)
        self.assertEqual(state.jobs, {})

    def test_unknown_job_returns_protocol_error(self) -> None:
        state = self.initialized_state()
        response = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "job.status",
                "params": {"jobId": "missing"},
            },
            state,
        )

        self.assertEqual(response["error"]["code"], -32011)


if __name__ == "__main__":
    unittest.main()
