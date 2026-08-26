# OpenRosalind Local Agent Worker Protocol v3

## Scope

This protocol connects the trusted Rust Desktop Core to one long-lived local
Python Agent Worker. It is shared by macOS and Windows. The Worker is not
started per Conversation or per AgentJob, and it does not run in Docker.

Version 3 adds credential-free model requests to the AgentJob lifecycle,
cancellation, and structured progress from v2. The Worker may ask Desktop Core
to run a bounded model request, but it cannot resolve credentials or access the
model network itself. Desktop Core remains the owner of Provider calls,
persisted state, cancellation, and recovery.

## Transport

- Desktop Core starts the Worker as a direct child process.
- Requests use Worker stdin; responses use Worker stdout.
- Each message is one UTF-8 JSON object followed by a newline.
- A message may not exceed 1 MiB.
- Desktop Core fails a request if no response arrives within 5 seconds.
- stdout is reserved for protocol responses. Diagnostics must not use stdout.
- Version 3 uses polling and sends no unsolicited Worker notifications.
- Desktop Core owns graceful shutdown and force termination.

## Initialization

Messages use JSON-RPC 2.0. Desktop Core assigns a monotonically increasing
numeric request ID, and the Worker returns the same ID.

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"client":"open-rosalind-desktop","protocolVersion":3}}
```

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": 3,
    "worker": "open-rosalind-local-agent",
    "capabilities": {
      "jobControl": true,
      "progressPolling": true,
      "toolCalls": false,
      "modelCredentials": false,
      "modelBrokerRequests": true
    }
  }
}
```

The Worker rejects every method except `initialize` until exact version
negotiation succeeds.

## Version 3 methods

| Method | Purpose |
|---|---|
| `initialize` | Negotiate the exact protocol version and capabilities |
| `ping` | Verify that the initialized Worker can respond |
| `job.start` | Register and asynchronously start one persisted AgentJob |
| `job.status` | Poll the current state and complete ordered progress snapshot |
| `job.cancel` | Request cooperative cancellation; idempotent for terminal jobs |
| `model.complete` | Return a sanitized Provider result or error for one pending request |
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
      "payload": {"protocolVersion": 3},
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

## Provider Broker round trip

A model AgentJob request contains only a Provider Profile reference, bounded
messages, and generation parameters. It never contains an API Key. The Worker
publishes a `pendingModelRequest` in its status snapshot:

```json
{
  "requestId": "5a77...",
  "providerProfileId": "default-qwen-openai-compatible",
  "messages": [{"role": "user", "content": "Summarize this paper"}],
  "temperature": 0.2
}
```

Desktop Core validates the request, resolves the profile and system-vault
credential, performs the HTTPS/SSE call, and sends `model.complete` with either
the sanitized result or a bounded error. The Worker receives only content,
model metadata, finish reason, and elapsed time. It never receives an
authorization header or credential value.

## State machine and recovery

Normal execution follows `queued -> running -> completed`. Cancellation uses
`queued -> cancelled` when the Worker has not started, or
`running -> cancelling -> cancelled` after start. Failures end in `failed`.

On Desktop Core startup, persisted `queued`, `running`, or `cancelling` jobs
from a previous process are changed to `interrupted`, assigned an end time, and
given a recovery event. Version 3 does not silently restart them because the
Worker's in-memory execution state no longer exists.

## Security invariants

- The Worker receives an environment allowlist, not the parent environment.
- Model API keys, OpenRosalind authentication tokens, GitHub tokens, and the
  loopback bootstrap token are not passed to the Worker.
- Version 3 cannot invoke Shell, Docker, network, filesystem, Provider
  credentials, or tools. Model network access belongs exclusively to Desktop
  Core.
- Non-model lifecycle results explicitly identify themselves as
  `lifecycle-stub-v3` and never claim model or tool work was performed.
- Only Desktop Core may later resolve a credential reference or approve a Tool
  Contract request.

## Future extension

A later protocol revision may add multi-step planning and Tool Contract
requests. Those capabilities must keep permission snapshots, ToolRuns,
Artifacts, credential resolution, cancellation, and audit records under
Desktop Core ownership.
