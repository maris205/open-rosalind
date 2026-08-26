"""Long-lived local Agent Worker protocol for OpenRosalind Desktop."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import BinaryIO


PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 1024 * 1024


@dataclass
class WorkerState:
    initialized: bool = False
    shutdown_requested: bool = False


def rpc_error(request_id: object, code: int, message: str) -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def handle_request(payload: object, state: WorkerState) -> dict[str, object]:
    if not isinstance(payload, dict):
        return rpc_error(None, -32600, "Invalid Request")
    request_id = payload.get("id")
    if payload.get("jsonrpc") != "2.0" or not isinstance(payload.get("method"), str):
        return rpc_error(request_id, -32600, "Invalid Request")
    params = payload.get("params", {})
    if not isinstance(params, dict):
        return rpc_error(request_id, -32602, "Invalid params")

    method = str(payload["method"])
    if method == "initialize":
        requested_version = params.get("protocolVersion")
        if requested_version != PROTOCOL_VERSION:
            return rpc_error(request_id, -32001, "Unsupported protocol version")
        state.initialized = True
        result: dict[str, object] = {
            "protocolVersion": PROTOCOL_VERSION,
            "worker": "open-rosalind-local-agent",
            "capabilities": {
                "jobControl": False,
                "toolCalls": False,
                "modelCredentials": False,
            },
        }
    elif not state.initialized:
        return rpc_error(request_id, -32002, "Worker is not initialized")
    elif method == "ping":
        result = {"ok": True, "protocolVersion": PROTOCOL_VERSION}
    elif method == "shutdown":
        state.shutdown_requested = True
        result = {"ok": True}
    else:
        return rpc_error(request_id, -32601, "Method not found")
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def serve(input_stream: BinaryIO, output_stream: BinaryIO) -> int:
    state = WorkerState()
    while not state.shutdown_requested:
        raw = input_stream.readline(MAX_MESSAGE_BYTES + 1)
        if not raw:
            break
        if len(raw) > MAX_MESSAGE_BYTES:
            response = rpc_error(None, -32600, "Request exceeds protocol limit")
            encoded = (json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8")
            output_stream.write(encoded)
            output_stream.flush()
            return 1
        else:
            try:
                response = handle_request(json.loads(raw), state)
            except (json.JSONDecodeError, UnicodeDecodeError):
                response = rpc_error(None, -32700, "Parse error")
        encoded = (json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        output_stream.write(encoded)
        output_stream.flush()
    return 0


def main() -> int:
    return serve(sys.stdin.buffer, sys.stdout.buffer)


if __name__ == "__main__":
    raise SystemExit(main())
