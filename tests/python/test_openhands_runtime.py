import unittest
from unittest.mock import patch

from web_app import openhands_runtime


class OpenHandsGatewayRecoveryTests(unittest.TestCase):
    def test_recover_gateway_timeout_waits_for_finished_conversation(self) -> None:
        responses = iter(
            [
                ({"items": [{"id": "conversation-1"}]}, {}),
                ({"execution_status": "running"}, {}),
                ({"execution_status": "finished"}, {}),
                ({"response": "recovered markdown"}, {}),
            ]
        )

        with patch.object(openhands_runtime, "request_json", side_effect=responses), patch.object(
            openhands_runtime.time, "sleep"
        ):
            response, headers = openhands_runtime._recover_gateway_timeout(
                server_url="http://127.0.0.1:1",
                session_api_key="test-key",
            )

        self.assertEqual(response["choices"][0]["message"]["content"], "recovered markdown")
        self.assertEqual(headers["x-openhands-serverconversation-id"], "conversation-1")

    def test_execute_recovers_only_for_exclusive_server(self) -> None:
        timeout = RuntimeError("OpenHands HTTP 504: Agent run timed out")
        recovered = ({"choices": [{"message": {"content": "done"}}]}, {})

        with patch.object(openhands_runtime, "ensure_profile"), patch.object(
            openhands_runtime, "request_json", side_effect=[timeout, recovered]
        ), patch.object(openhands_runtime, "_recover_gateway_timeout", return_value=recovered):
            result = openhands_runtime._execute_against_server(
                "system",
                "task",
                server_url="http://127.0.0.1:1",
                session_api_key="test-key",
                exclusive_server=True,
            )

        self.assertEqual(result["content"], "done")


if __name__ == "__main__":
    unittest.main()
