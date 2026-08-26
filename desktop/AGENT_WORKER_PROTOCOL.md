# OpenRosalind Local Agent Worker Protocol v2

## Scope

This protocol connects the trusted Rust Desktop Core to one long-lived local
Python Agent Worker. It is shared by macOS and Windows. The Worker is not
started per Conversation or per AgentJob, and it does not run in Docker.

Version 2 adds an AgentJob lifecycle, cancellation, and structured progress.
The implementation is deliberately a lifecycle stub: it does not call a model
or expose Shell, Docker, network, filesystem, or tool capabilities. Desktop
Core remains the owner of persisted state and recovery.

## Transport

- Desktop Core starts the Worker as a direct child process.
- Requests use Worker stdin; responses use Worker stdout.
- Each message is one UTF-8 JSON object followed by a newline.
- A message may not exceed 1 MiB.
- Desktop Core fails a request if no response arrives within 5 seconds.
- stdout is reserved for protocol responses. Diagnostics must not use stdout.
- Version 2 uses polling and sends no unsolicited Worker notifications.
- Desktop Core owns graceful shutdown and force termination.

## Initialization

Messages use JSON-RPC 2.0. Desktop Core assigns a monotonically increasing
numeric request ID, and the Worker returns the same ID.

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"client":"open-rosalind-desktop","protocolVersion":2}}
```

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": 2,
    "worker": "open-rosalind-local-agent",
    "capabilities": {
      "jobControl": true,
      "progressPolling": true,
      "toolCalls": false,
      "modelCredentials": false
    }
  }
}
```

The Worker rejects every method except `initialize` until exact version
negotiation succeeds.

## Version 2 methods

| Method | Purpose |
|---|---|
| `initialize` | Negotiate the exact protocol version and capabilities |
| `ping` | Verify that the initialized Worker can respond |
| `job.start` | Register and asynchronously start one persisted AgentJob |
| `job.status` | Poll the current state and complete ordered progress snapshot |
| `job.cancel` | Request cooperative cancellation; idempotent for terminal jobs |
| `shutdown` | Request cancellation of active jobs, acknowledge, and exit |

`job.start` accepts a Desktop-Core-assigned `jobId` and a JSON object request.
Duplicate job IDs fail. Requests containing secret-shaped fields fail at both
the Desktop Core persistence boundary and the Worker boundary.

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "job.start",
  "params": {
    "jobId": "0f3d...",
    "request": {"input": "Prepare a research plan"}
  }
}
```

All three job methods return the same snapshot shape:

```json
{
  "jobId": "0f3d...",
  "status": "running",
  "cancellationRequested": false,
  "progress": [
    {
      "sequence": 1,
      "kind": "accepted",
      "payload": {"protocolVersion": 2},
      "createdAt": 1787700000000
    }
  ],
  "result": null,
  "error": null,
  "startedAt": 1787700000001,
  "endedAt": null
}
```

Progress snapshots are cumulative. Desktop Core persists them with a unique
`(agent_job_id, sequence)` key, making repeated status polling idempotent.

## State machine and recovery

Normal execution follows `queued -> running -> completed`. Cancellation uses
`queued -> cancelled` when the Worker has not started, or
`running -> cancelling -> cancelled` after start. Failures end in `failed`.

On Desktop Core startup, persisted `queued`, `running`, or `cancelling` jobs
from a previous process are changed to `interrupted`, assigned an end time, and
given a recovery event. Version 2 does not silently restart them because the
Worker's in-memory execution state no longer exists.

## Security invariants

- The Worker receives an environment allowlist, not the parent environment.
- Model API keys, OpenRosalind authentication tokens, GitHub tokens, and the
  loopback bootstrap token are not passed to the Worker.
- Version 2 cannot invoke Shell, Docker, network, filesystem, models, or tools.
- The lifecycle result explicitly identifies itself as `lifecycle-stub-v2` and
  never claims that model or tool work was performed.
- Only Desktop Core may later resolve a credential reference or approve a Tool
  Contract request.

## Future extension

A later protocol revision may add model execution and Tool Contract requests.
Those capabilities must keep permission snapshots, ToolRuns, Artifacts,
credential resolution, cancellation, and audit records under Desktop Core
ownership.
