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
                "params": {"client": "test-suite", "protocolVersion": 4},
            },
            state,
        )
        self.assertEqual(response["result"]["protocolVersion"], 4)
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
                    "protocolVersion": 4,
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
        self.assertEqual(responses[0]["result"]["protocolVersion"], 4)
        self.assertTrue(responses[0]["result"]["capabilities"]["jobControl"])
        self.assertFalse(responses[0]["result"]["capabilities"]["modelCredentials"])
        self.assertTrue(responses[0]["result"]["capabilities"]["modelBrokerRequests"])
        self.assertTrue(responses[0]["result"]["capabilities"]["toolCalls"])
        self.assertEqual(
            responses[0]["result"]["capabilities"]["automaticTools"],
            ["project.file.read", "project.files.list", "text.statistics"],
        )
        self.assertEqual(
            responses[0]["result"]["capabilities"]["approvalRequiredTools"],
            ["project.file.write"],
        )
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
        self.assertEqual(result["result"]["mode"], "lifecycle-stub-v4")
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

    def test_model_job_round_trip_never_contains_credentials(self) -> None:
        state = self.initialized_state()
        handle_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "job.start",
                "params": {
                    "jobId": "job-model",
                    "request": {
                        "mode": "model",
                        "providerProfileId": "profile-1",
                        "messages": [
                            {"role": "system", "content": "Be concise."},
                            {"role": "user", "content": "Summarize the result."},
                        ],
                        "temperature": 0.2,
                    },
                },
            },
            state,
        )

        pending = None
        for request_id in range(3, 30):
            snapshot = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "job.status",
                    "params": {"jobId": "job-model"},
                },
                state,
            )
            pending = snapshot["result"]["pendingModelRequest"]
            if pending:
                break
            time.sleep(0.01)

        self.assertIsNotNone(pending)
        self.assertEqual(pending["providerProfileId"], "profile-1")
        encoded_pending = json.dumps(pending)
        self.assertNotIn("apiKey", encoded_pending)
        self.assertNotIn("credential", encoded_pending.lower())

        completed = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 30,
                "method": "model.complete",
                "params": {
                    "jobId": "job-model",
                    "requestId": pending["requestId"],
                    "result": {
                        "content": "A brokered answer.",
                        "model": "test-model",
                        "finishReason": "stop",
                        "elapsedMillis": 12,
                    },
                },
            },
            state,
        )
        for request_id in range(31, 60):
            completed = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "job.status",
                    "params": {"jobId": "job-model"},
                },
                state,
            )
            if completed["result"]["status"] == "completed":
                break
            time.sleep(0.01)

        self.assertEqual(completed["result"]["status"], "completed")
        self.assertEqual(completed["result"]["result"]["mode"], "tool-agent-v4")
        self.assertEqual(completed["result"]["result"]["content"], "A brokered answer.")

    def test_agent_closes_model_tool_model_loop_without_credentials(self) -> None:
        state = self.initialized_state()
        handle_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "job.start",
                "params": {
                    "jobId": "job-tool-loop",
                    "request": {
                        "mode": "agent",
                        "providerProfileId": "profile-1",
                        "messages": [{"role": "user", "content": "Count these words: a b c"}],
                        "temperature": 0.2,
                    },
                },
            },
            state,
        )

        first_model = None
        for request_id in range(3, 30):
            snapshot = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "job.status",
                    "params": {"jobId": "job-tool-loop"},
                },
                state,
            )
            first_model = snapshot["result"]["pendingModelRequest"]
            if first_model:
                break
            time.sleep(0.01)
        self.assertIsNotNone(first_model)
        handle_request(
            {
                "jsonrpc": "2.0",
                "id": 30,
                "method": "model.complete",
                "params": {
                    "jobId": "job-tool-loop",
                    "requestId": first_model["requestId"],
                    "result": {
                        "content": json.dumps(
                            {
                                "type": "tool",
                                "tool": "text.statistics",
                                "input": {"text": "a b c"},
                            }
                        ),
                        "model": "test-model",
                        "finishReason": "stop",
                        "elapsedMillis": 3,
                    },
                },
            },
            state,
        )

        pending_tool = None
        for request_id in range(31, 60):
            snapshot = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "job.status",
                    "params": {"jobId": "job-tool-loop"},
                },
                state,
            )
            pending_tool = snapshot["result"]["pendingToolRequest"]
            if pending_tool:
                break
            time.sleep(0.01)
        self.assertEqual(pending_tool["toolName"], "text.statistics")
        self.assertEqual(pending_tool["input"], {"text": "a b c"})
        handle_request(
            {
                "jsonrpc": "2.0",
                "id": 60,
                "method": "tool.complete",
                "params": {
                    "jobId": "job-tool-loop",
                    "requestId": pending_tool["requestId"],
                    "result": {
                        "toolRunId": "run-1",
                        "status": "succeeded",
                        "output": {"words": 3},
                    },
                },
            },
            state,
        )

        second_model = None
        for request_id in range(61, 90):
            snapshot = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "job.status",
                    "params": {"jobId": "job-tool-loop"},
                },
                state,
            )
            second_model = snapshot["result"]["pendingModelRequest"]
            if second_model:
                break
            time.sleep(0.01)
        self.assertIsNotNone(second_model)
        encoded_messages = json.dumps(second_model["messages"])
        self.assertIn("untrusted data", encoded_messages)
        self.assertIn('"words":3', second_model["messages"][-1]["content"])
        self.assertNotIn("apiKey", encoded_messages)
        handle_request(
            {
                "jsonrpc": "2.0",
                "id": 90,
                "method": "model.complete",
                "params": {
                    "jobId": "job-tool-loop",
                    "requestId": second_model["requestId"],
                    "result": {
                        "content": json.dumps({"type": "final", "content": "There are 3 words."}),
                        "model": "test-model",
                        "finishReason": "stop",
                        "elapsedMillis": 4,
                    },
                },
            },
            state,
        )
        completed = None
        for request_id in range(91, 120):
            completed = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "job.status",
                    "params": {"jobId": "job-tool-loop"},
                },
                state,
            )
            if completed["result"]["status"] == "completed":
                break
            time.sleep(0.01)
        result = completed["result"]["result"]
        self.assertEqual(result["content"], "There are 3 words.")
        self.assertEqual(result["toolRuns"][0]["toolRunId"], "run-1")
        self.assertEqual(result["toolRuns"][0]["status"], "succeeded")

    def test_agent_rejects_high_risk_tool_before_desktop_execution(self) -> None:
        state = self.initialized_state()
        handle_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "job.start",
                "params": {
                    "jobId": "job-high-risk-tool",
                    "request": {
                        "mode": "agent",
                        "messages": [{"role": "user", "content": "Run Python"}],
                    },
                },
            },
            state,
        )
        pending = None
        for request_id in range(3, 30):
            snapshot = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "job.status",
                    "params": {"jobId": "job-high-risk-tool"},
                },
                state,
            )
            pending = snapshot["result"]["pendingModelRequest"]
            if pending:
                break
            time.sleep(0.01)
        handle_request(
            {
                "jsonrpc": "2.0",
                "id": 30,
                "method": "model.complete",
                "params": {
                    "jobId": "job-high-risk-tool",
                    "requestId": pending["requestId"],
                    "result": {
                        "content": json.dumps(
                            {
                                "type": "tool",
                                "tool": "python.run",
                                "input": {"code": "print('no')"},
                            }
                        ),
                        "model": "test-model",
                    },
                },
            },
            state,
        )
        completed = None
        for request_id in range(31, 60):
            completed = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "job.status",
                    "params": {"jobId": "job-high-risk-tool"},
                },
                state,
            )
            if completed["result"]["status"] == "failed":
                break
            time.sleep(0.01)
        self.assertIn("not available for automatic", completed["result"]["error"])
        self.assertIsNone(completed["result"]["pendingToolRequest"])

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

    def test_project_write_reaches_desktop_core_for_user_approval(self) -> None:
        state = self.initialized_state()
        handle_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "job.start",
                "params": {
                    "jobId": "job-project-write",
                    "request": {
                        "mode": "agent",
                        "messages": [{"role": "user", "content": "Create notes.md"}],
                    },
                },
            },
            state,
        )
        pending_model = None
        for request_id in range(3, 30):
            snapshot = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "job.status",
                    "params": {"jobId": "job-project-write"},
                },
                state,
            )
            pending_model = snapshot["result"]["pendingModelRequest"]
            if pending_model:
                break
            time.sleep(0.01)
        handle_request(
            {
                "jsonrpc": "2.0",
                "id": 30,
                "method": "model.complete",
                "params": {
                    "jobId": "job-project-write",
                    "requestId": pending_model["requestId"],
                    "result": {
                        "content": json.dumps(
                            {
                                "type": "tool",
                                "tool": "project.file.write",
                                "input": {"path": "notes.md", "content": "review me"},
                            }
                        ),
                        "model": "test-model",
                    },
                },
            },
            state,
        )
        pending_tool = None
        for request_id in range(31, 60):
            snapshot = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "job.status",
                    "params": {"jobId": "job-project-write"},
                },
                state,
            )
            pending_tool = snapshot["result"]["pendingToolRequest"]
            if pending_tool:
                break
            time.sleep(0.01)
        self.assertEqual(pending_tool["toolName"], "project.file.write")
        self.assertEqual(pending_tool["input"]["path"], "notes.md")
        self.assertEqual(pending_tool["input"]["content"], "review me")


if __name__ == "__main__":
    unittest.main()
