"""OpenHands Agent Server adapter for Rosalind task-step execution."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator
from typing import Any


SERVER_URL = os.environ.get("OPENHANDS_AGENT_SERVER_URL", "http://127.0.0.1:3001").rstrip("/")
SESSION_API_KEY = os.environ.get("OPENHANDS_SESSION_API_KEY", "")
PROFILE_NAME = os.environ.get("OPENHANDS_PROFILE", "rosalind")
GATEWAY_MODEL = f"openhands_{PROFILE_NAME}"
REQUEST_TIMEOUT = int(os.environ.get("OPENHANDS_REQUEST_TIMEOUT", "900"))
ISOLATED_EXECUTION = os.environ.get("OPENHANDS_ISOLATED_EXECUTION", "0") == "1"
AGENT_SERVER_IMAGE = os.environ.get(
    "OPENHANDS_AGENT_SERVER_IMAGE",
    "ghcr.io/openhands/agent-server:latest-python",
)
HOST_PROJECTS_ROOT = Path(
    os.environ.get(
        "OPENHANDS_HOST_PROJECTS_ROOT",
        Path(__file__).resolve().parents[1] / "data" / "agent-workspaces",
    )
)
HOST_RUNS_ROOT = Path(
    os.environ.get(
        "OPENHANDS_HOST_RUNS_ROOT",
        Path(__file__).resolve().parents[1] / "data" / "openhands-runs",
    )
)
SKILLS_DIR = Path(__file__).resolve().parents[1] / ".openhands"
CONTAINER_UID = int(os.environ.get("OPENHANDS_CONTAINER_UID", "10001"))
CONTAINER_GID = int(os.environ.get("OPENHANDS_CONTAINER_GID", "10001"))
CONTAINER_START_TIMEOUT = int(os.environ.get("OPENHANDS_CONTAINER_START_TIMEOUT", "90"))
CONTAINER_MEMORY = os.environ.get("OPENHANDS_CONTAINER_MEMORY", "2g")
CONTAINER_CPUS = os.environ.get("OPENHANDS_CONTAINER_CPUS", "2")


def gateway_model_name(model: str, base_url: str) -> str:
    """Return a LiteLLM model identifier for OpenAI-compatible endpoints."""
    normalized = model.strip()
    if base_url and "/" not in normalized:
        return f"openai/{normalized}"
    return normalized


def request_json(
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    authorization: bool = False,
    timeout: int = 30,
    server_url: str | None = None,
    session_api_key: str | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    target_server = (server_url or SERVER_URL).rstrip("/")
    target_key = SESSION_API_KEY if session_api_key is None else session_api_key
    raw = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if target_key:
        if authorization:
            headers["Authorization"] = f"Bearer {target_key}"
        else:
            headers["X-Session-API-Key"] = target_key
    request = urllib.request.Request(
        f"{target_server}{path}",
        data=raw,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            return body, {name.lower(): value for name, value in response.headers.items()}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenHands HTTP {exc.code}: {detail[-4000:]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"OpenHands Agent Server unavailable: {exc}") from exc


def health() -> dict[str, Any]:
    if ISOLATED_EXECUTION:
        try:
            _docker(["info", "--format", "{{.ServerVersion}}"], timeout=5)
            _docker(["image", "inspect", AGENT_SERVER_IMAGE], timeout=5)
            return {
                "ok": True,
                "runtime": "ephemeral-container",
                "isolatedExecution": True,
                "image": AGENT_SERVER_IMAGE,
                "details": {"docker": "ready", "image": "ready"},
            }
        except Exception as exc:  # noqa: BLE001 - health endpoint should be bounded
            return {
                "ok": False,
                "runtime": "ephemeral-container",
                "isolatedExecution": True,
                "image": AGENT_SERVER_IMAGE,
                "error": str(exc),
            }
    try:
        data, _headers = request_json("/health", timeout=5)
        return {
            "ok": True,
            "server": SERVER_URL,
            "isolatedExecution": ISOLATED_EXECUTION,
            "details": data,
        }
    except Exception as exc:  # noqa: BLE001 - health endpoint should be bounded
        return {
            "ok": False,
            "server": SERVER_URL,
            "isolatedExecution": ISOLATED_EXECUTION,
            "error": str(exc),
        }


def ensure_profile(*, server_url: str = SERVER_URL, session_api_key: str = SESSION_API_KEY) -> None:
    api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("QWEN_BASE_URL") or os.environ.get("OPENAI_BASE_URL", "")
    model = os.environ.get("QWEN_MODEL") or os.environ.get("OPENAI_MODEL", "qwen3.7-max")
    if not api_key:
        raise RuntimeError("OpenHands profile requires DASHSCOPE_API_KEY or OPENAI_API_KEY.")
    llm: dict[str, Any] = {
        "model": gateway_model_name(model, base_url),
        "api_key": api_key,
    }
    if base_url:
        llm["base_url"] = base_url
    try:
        request_json(
            f"/api/profiles/{PROFILE_NAME}",
            method="POST",
            payload={"llm": llm, "include_secrets": True},
            timeout=30,
            server_url=server_url,
            session_api_key=session_api_key,
        )
    except RuntimeError as exc:
        # The profile API returns a conflict when an identical profile already exists.
        if "HTTP 409" not in str(exc):
            raise


def workspace_for_project(user_id: str, project_id: str) -> Path:
    """Return a stable host path for one user's project without exposing IDs."""
    user_key = hashlib.sha256(f"user:{user_id}".encode()).hexdigest()[:24]
    project_key = hashlib.sha256(f"project:{project_id}".encode()).hexdigest()[:24]
    workspace = HOST_PROJECTS_ROOT / user_key / project_key
    workspace.mkdir(parents=True, exist_ok=True)
    workspace.chmod(0o700)
    os.chown(workspace, CONTAINER_UID, CONTAINER_GID)
    return workspace


def _docker(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["docker", *command],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "Docker command failed."
        raise RuntimeError(detail[-4000:])
    return completed


def cleanup_isolated_containers() -> int:
    """Remove containers orphaned by a previously interrupted worker."""
    if not ISOLATED_EXECUTION:
        return 0
    listed = _docker([
        "ps", "-aq",
        "--filter", "label=open-rosalind.runtime=isolated",
    ])
    container_ids = [item for item in listed.stdout.splitlines() if item.strip()]
    for container_id in container_ids:
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_id],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except subprocess.TimeoutExpired:
            continue
    return len(container_ids)


def _container_port(container_name: str) -> int:
    inspected = json.loads(_docker(["inspect", container_name]).stdout)
    bindings = inspected[0]["NetworkSettings"]["Ports"]["8000/tcp"]
    if not bindings:
        raise RuntimeError("OpenHands isolated container has no published port.")
    return int(bindings[0]["HostPort"])


def _wait_for_server(server_url: str, session_api_key: str, container_name: str) -> None:
    deadline = time.monotonic() + CONTAINER_START_TIMEOUT
    last_error = ""
    while time.monotonic() < deadline:
        try:
            request_json(
                "/health",
                timeout=3,
                server_url=server_url,
                session_api_key=session_api_key,
            )
            return
        except Exception as exc:  # noqa: BLE001 - bounded startup polling
            last_error = str(exc)
            time.sleep(1)
    logs = _docker(["logs", "--tail", "120", container_name], timeout=20).stdout
    raise RuntimeError(f"OpenHands isolated container did not become ready: {last_error}\n{logs[-4000:]}")


@contextmanager
def isolated_server(workspace_path: Path) -> Iterator[tuple[str, str]]:
    """Run one ephemeral Agent Server that can see only one project workspace."""
    if workspace_path.is_symlink():
        raise RuntimeError("OpenHands workspace cannot be a symlink.")
    workspace = workspace_path.resolve()
    if not workspace.is_dir():
        raise RuntimeError(f"OpenHands workspace does not exist: {workspace}")

    run_id = uuid.uuid4().hex
    runtime_dir = (HOST_RUNS_ROOT / run_id).resolve()
    runtime_dir.mkdir(parents=True, mode=0o700)
    os.chown(runtime_dir, CONTAINER_UID, CONTAINER_GID)
    container_name = f"open-rosalind-oh-{run_id[:12]}"
    session_api_key = secrets.token_urlsafe(32)
    secret_key = secrets.token_urlsafe(48)
    docker_env = os.environ.copy()
    docker_env.update({"SESSION_API_KEY": session_api_key, "OH_SECRET_KEY": secret_key})

    command = [
        "run", "-d", "--rm",
        "--name", container_name,
        "--pull", "never",
        "--label", "open-rosalind.runtime=isolated",
        "--label", f"open-rosalind.run_id={run_id}",
        "--memory", CONTAINER_MEMORY,
        "--cpus", CONTAINER_CPUS,
        "--pids-limit", "512",
        "--security-opt", "no-new-privileges",
        "-p", "127.0.0.1::8000",
        "-e", "SESSION_API_KEY",
        "-e", "OH_SECRET_KEY",
        "-e", "OH_ENABLE_VNC=0",
        "-e", "OH_ENABLE_VSCODE=0",
        "-e", "OH_PRELOAD_TOOLS=1",
        "-e", "OH_PERSISTENCE_DIR=/workspace/.state",
        "-v", f"{runtime_dir}:/workspace",
        "-v", f"{workspace}:/workspace/project",
        "-v", f"{SKILLS_DIR}:/workspace/.openhands:ro",
        "-w", "/",
        AGENT_SERVER_IMAGE,
    ]
    started = False
    try:
        _docker(command, env=docker_env, timeout=120)
        started = True
        server_url = f"http://127.0.0.1:{_container_port(container_name)}"
        _wait_for_server(server_url, session_api_key, container_name)
        yield server_url, session_api_key
    finally:
        if started:
            try:
                subprocess.run(
                    ["docker", "stop", "-t", "10", container_name],
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                subprocess.run(
                    ["docker", "rm", "-f", container_name],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )


def _execute_against_server(
    system_prompt: str,
    task_input: str,
    *,
    server_url: str,
    session_api_key: str,
    exclusive_server: bool = False,
) -> dict[str, Any]:
    ensure_profile(server_url=server_url, session_api_key=session_api_key)
    payload = {
        "model": GATEWAY_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task_input},
        ],
        "temperature": 0.2,
    }
    try:
        response, headers = request_json(
            "/v1/chat/completions",
            method="POST",
            payload=payload,
            authorization=True,
            timeout=REQUEST_TIMEOUT,
            server_url=server_url,
            session_api_key=session_api_key,
        )
    except RuntimeError as exc:
        gateway_timed_out = "OpenHands HTTP 504" in str(exc) and "Agent run timed out" in str(exc)
        if not exclusive_server or not gateway_timed_out:
            raise
        response, headers = _recover_gateway_timeout(
            server_url=server_url,
            session_api_key=session_api_key,
        )
    content = str(response.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()
    if not content:
        raise RuntimeError("OpenHands completed without a textual result.")
    conversation_id = headers.get("x-openhands-serverconversation-id", "")
    return {
        "ok": True,
        "runtime": "openhands",
        "conversationId": conversation_id,
        "content": content,
        "raw": response,
    }


def _recover_gateway_timeout(*, server_url: str, session_api_key: str) -> tuple[dict[str, Any], dict[str, str]]:
    """Wait past Agent Server's 120-second OpenAI gateway limit.

    An isolated server owns exactly one conversation, so its newest conversation
    is the request that just timed out. The agent keeps running after the gateway
    returns 504; polling the native API preserves that work instead of destroying
    the ephemeral container and starting over.
    """
    search, _headers = request_json(
        "/api/conversations/search?limit=1",
        timeout=15,
        server_url=server_url,
        session_api_key=session_api_key,
    )
    items = search.get("items", [])
    if not items or not items[0].get("id"):
        raise RuntimeError("OpenHands gateway timed out and its conversation could not be recovered.")
    conversation_id = str(items[0]["id"])
    deadline = time.monotonic() + REQUEST_TIMEOUT

    while time.monotonic() < deadline:
        conversation, _headers = request_json(
            f"/api/conversations/{conversation_id}",
            timeout=15,
            server_url=server_url,
            session_api_key=session_api_key,
        )
        status = str(conversation.get("execution_status", ""))
        if status == "finished":
            final, _headers = request_json(
                f"/api/conversations/{conversation_id}/agent_final_response",
                timeout=15,
                server_url=server_url,
                session_api_key=session_api_key,
            )
            content = str(final.get("response", "")).strip()
            if not content:
                raise RuntimeError("OpenHands finished after the gateway timeout without a textual result.")
            return (
                {"choices": [{"message": {"content": content}}], "recoveredAfterGatewayTimeout": True},
                {"x-openhands-serverconversation-id": conversation_id},
            )
        if status in {"error", "stuck", "paused", "waiting_for_confirmation"}:
            raise RuntimeError(f"OpenHands run ended with status: {status}")
        time.sleep(2)

    raise RuntimeError(f"OpenHands run did not finish within {REQUEST_TIMEOUT} seconds after gateway timeout.")


def execute_step(
    system_prompt: str,
    task_input: str,
    *,
    workspace_path: Path | str | None = None,
) -> dict[str, Any]:
    if ISOLATED_EXECUTION:
        if workspace_path is None:
            raise RuntimeError("Isolated OpenHands execution requires a project workspace.")
        with isolated_server(Path(workspace_path)) as (server_url, session_api_key):
            result = _execute_against_server(
                system_prompt,
                task_input,
                server_url=server_url,
                session_api_key=session_api_key,
                exclusive_server=True,
            )
            result["isolation"] = "ephemeral-container"
            return result
    return _execute_against_server(
        system_prompt,
        task_input,
        server_url=SERVER_URL,
        session_api_key=SESSION_API_KEY,
    )
