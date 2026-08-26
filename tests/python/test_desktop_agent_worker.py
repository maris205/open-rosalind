import json
import os
import subprocess
import sys
import unittest
from io import BytesIO

from web_app.desktop_agent_worker import (
    MAX_MESSAGE_BYTES,
    WorkerState,
    handle_request,
    serve,
)


class DesktopAgentWorkerTests(unittest.TestCase):
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
                    "protocolVersion": 1,
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
        self.assertEqual(responses[0]["result"]["protocolVersion"], 1)
        self.assertFalse(responses[0]["result"]["capabilities"]["modelCredentials"])
        self.assertTrue(responses[1]["result"]["ok"])
        self.assertTrue(responses[2]["result"]["ok"])


if __name__ == "__main__":
    unittest.main()
