# OpenRosalind Local Agent Worker Protocol v1

## Scope

This protocol connects the trusted Rust Desktop Core to one long-lived local
Python Agent Worker. It is shared by macOS and Windows. The Worker is not
started per Conversation or per AgentJob, and it does not run in Docker.

Version 1 establishes only process lifecycle and protocol compatibility. Agent
execution and tools will be added through versioned capabilities after the
permission and Tool Contract layers exist.

## Transport

- Desktop Core starts the Worker as a direct child process.
- Requests use Worker stdin; responses use Worker stdout.
- Each message is one UTF-8 JSON object followed by a newline.
- A message may not exceed 1 MiB.
- Desktop Core fails a request if no response arrives within 5 seconds.
- stdout is reserved for protocol messages. Diagnostics must not be written to
  stdout.
- Desktop Core owns shutdown and force termination.

## JSON-RPC

Messages use JSON-RPC 2.0 request and response shapes. Desktop Core assigns a
monotonically increasing numeric request ID. The Worker must return the same ID
and protocol version.

Initialization request:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"client":"open-rosalind-desktop","protocolVersion":1}}
```

Initialization result:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": 1,
    "worker": "open-rosalind-local-agent",
    "capabilities": {
      "jobControl": false,
      "toolCalls": false,
      "modelCredentials": false
    }
  }
}
```

The Worker rejects every method except `initialize` until a compatible
initialization succeeds.

## Version 1 methods

| Method | Purpose |
|---|---|
| `initialize` | Negotiate the exact protocol version and capabilities |
| `ping` | Verify that the initialized Worker can respond |
| `shutdown` | Acknowledge graceful shutdown and exit the read loop |

Unknown methods return JSON-RPC error `-32601`. Invalid messages, parameters,
and versions fail closed.

## Security invariants

- The Worker receives an environment allowlist, not the parent process
  environment.
- Model API keys, OpenRosalind authentication tokens, GitHub tokens, and the
  loopback bootstrap token are not passed to the Worker.
- Version 1 cannot invoke Shell, Docker, network, filesystem, models, or tools.
- AgentJob payloads may contain credential references in future versions, but
  Desktop Core rejects embedded fields such as `apiKey`, `authorization`,
  `password`, `secret`, and `token` before persistence.
- Only Desktop Core may later resolve a credential reference or approve a Tool
  Contract request.

## Planned extension

The next protocol revision may add `job.start`, `job.cancel`, progress events,
and Tool Contract requests. These methods must keep AgentJob cancellation,
permission snapshots, ToolRuns, and Artifacts under Desktop Core ownership.
