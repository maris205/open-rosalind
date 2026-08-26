"""Long-lived local Agent Worker protocol for OpenRosalind Desktop."""

from __future__ import annotations

import json
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import BinaryIO


PROTOCOL_VERSION = 2
MAX_MESSAGE_BYTES = 1024 * 1024
MAX_JOB_ID_LENGTH = 128
MAX_LIFECYCLE_WORK_UNITS = 50
TERMINAL_STATUSES = frozenset({"completed", "cancelled", "failed"})


def unix_millis() -> int:
    return time.time_ns() // 1_000_000


@dataclass
class LocalJob:
    job_id: str
    request: dict[str, object]
    status: str = "queued"
    cancellation_requested: bool = False
    progress: list[dict[str, object]] = field(default_factory=list)
    result: dict[str, object] | None = None
    error: str | None = None
    started_at: int | None = None
    ended_at: int | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)


@dataclass
class WorkerState:
    initialized: bool = False
    shutdown_requested: bool = False
    jobs: dict[str, LocalJob] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)


def rpc_error(request_id: object, code: int, message: str) -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def contains_secret_field(value: object) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = "".join(character.lower() for character in str(key) if character.isalnum())
            if normalized in {
                "apikey",
                "authorization",
                "credential",
                "credentials",
                "password",
                "secret",
                "token",
            }:
                return True
            if contains_secret_field(child):
                return True
    elif isinstance(value, list):
        return any(contains_secret_field(child) for child in value)
    return False


def append_progress(job: LocalJob, kind: str, payload: dict[str, object]) -> None:
    job.progress.append(
        {
            "sequence": len(job.progress) + 1,
            "kind": kind,
            "payload": payload,
            "createdAt": unix_millis(),
        }
    )


def job_snapshot(job: LocalJob) -> dict[str, object]:
    return {
        "jobId": job.job_id,
        "status": job.status,
        "cancellationRequested": job.cancellation_requested,
        "progress": [dict(event) for event in job.progress],
        "result": job.result,
        "error": job.error,
        "startedAt": job.started_at,
        "endedAt": job.ended_at,
    }


def lifecycle_work_units(request: dict[str, object]) -> int:
    value = request.get("lifecycleWorkUnits", 3)
    if isinstance(value, bool) or not isinstance(value, int):
        return 3
    return max(1, min(value, MAX_LIFECYCLE_WORK_UNITS))


def run_lifecycle_job(state: WorkerState, job_id: str) -> None:
    with state.lock:
        job = state.jobs[job_id]
        if job.cancel_event.is_set():
            job.status = "cancelled"
            job.ended_at = unix_millis()
            append_progress(job, "cancelled", {"reason": "cancelled-before-start"})
            return
        work_units = lifecycle_work_units(job.request)

    try:
        for index in range(work_units):
            if job.cancel_event.wait(0.02):
                with state.lock:
                    job.status = "cancelled"
                    job.cancellation_requested = True
                    job.ended_at = unix_millis()
                    append_progress(job, "cancelled", {"completedUnits": index})
                return
            with state.lock:
                append_progress(
                    job,
                    "progress",
                    {"completedUnits": index + 1, "totalUnits": work_units},
                )

        with state.lock:
            job.status = "completed"
            job.result = {
                "mode": "lifecycle-stub-v2",
                "summary": "AgentJob lifecycle completed without model or tool execution",
                "inputLength": len(json.dumps(job.request, ensure_ascii=False)),
            }
            job.ended_at = unix_millis()
            append_progress(job, "completed", {"totalUnits": work_units})
    except Exception as error:  # pragma: no cover - last-resort worker boundary
        with state.lock:
            job.status = "failed"
            job.error = f"Lifecycle worker failed: {type(error).__name__}"
            job.ended_at = unix_millis()
            append_progress(job, "failed", {"errorType": type(error).__name__})


def validate_job_params(params: dict[str, object]) -> tuple[str | None, dict[str, object] | None, str | None]:
    job_id = params.get("jobId")
    if not isinstance(job_id, str) or not job_id.strip() or len(job_id) > MAX_JOB_ID_LENGTH:
        return None, None, "jobId must contain 1 to 128 characters"
    request = params.get("request")
    if not isinstance(request, dict):
        return None, None, "request must be a JSON object"
    if contains_secret_field(request):
        return None, None, "request must reference credentials, not contain secrets"
    return job_id, request, None


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
                "jobControl": True,
                "progressPolling": True,
                "toolCalls": False,
                "modelCredentials": False,
            },
        }
    elif not state.initialized:
        return rpc_error(request_id, -32002, "Worker is not initialized")
    elif method == "ping":
        result = {"ok": True, "protocolVersion": PROTOCOL_VERSION}
    elif method == "job.start":
        job_id, request, validation_error = validate_job_params(params)
        if validation_error is not None or job_id is None or request is None:
            return rpc_error(request_id, -32602, validation_error or "Invalid params")
        with state.lock:
            if job_id in state.jobs:
                return rpc_error(request_id, -32010, "AgentJob already exists")
            job = LocalJob(job_id=job_id, request=request)
            append_progress(job, "accepted", {"protocolVersion": PROTOCOL_VERSION})
            job.status = "running"
            job.started_at = unix_millis()
            append_progress(job, "started", {"executor": "lifecycle-stub-v2"})
            state.jobs[job_id] = job
            result = job_snapshot(job)
        threading.Thread(
            target=run_lifecycle_job,
            args=(state, job_id),
            name=f"agent-job-{job_id[:24]}",
            daemon=True,
        ).start()
    elif method == "job.status":
        job_id = params.get("jobId")
        if not isinstance(job_id, str) or not job_id:
            return rpc_error(request_id, -32602, "jobId is required")
        with state.lock:
            job = state.jobs.get(job_id)
            if job is None:
                return rpc_error(request_id, -32011, "AgentJob was not found")
            result = job_snapshot(job)
    elif method == "job.cancel":
        job_id = params.get("jobId")
        if not isinstance(job_id, str) or not job_id:
            return rpc_error(request_id, -32602, "jobId is required")
        with state.lock:
            job = state.jobs.get(job_id)
            if job is None:
                return rpc_error(request_id, -32011, "AgentJob was not found")
            if job.status not in TERMINAL_STATUSES:
                job.cancellation_requested = True
                job.status = "cancelling"
                job.cancel_event.set()
                append_progress(job, "cancellation_requested", {})
            result = job_snapshot(job)
    elif method == "shutdown":
        state.shutdown_requested = True
        with state.lock:
            for job in state.jobs.values():
                if job.status not in TERMINAL_STATUSES:
                    job.cancellation_requested = True
                    job.cancel_event.set()
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
