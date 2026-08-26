# OpenRosalind Desktop Alpha

The desktop alpha wraps the existing OpenRosalind web application in Tauri and
starts the same Python API locally. Skills, task planning, report generation,
message presentation, and biomedical tools remain shared with the web build.

## Current Runtime

- The local API binds to a random loopback port by default. Tauri generates a
  per-launch transport token and exchanges it for an HttpOnly, SameSite cookie
  before the shared UI can access the local API.
- SQLite data, generated jobs, and Agent workspaces live in the operating
  system's application-data directory.
- Agent jobs use an in-process background queue, so Redis and an RQ worker are
  not required.
- A separate, long-lived local Agent Worker starts outside Docker and performs
  a versioned JSON-RPC handshake over stdio. The initial protocol exposes only
  lifecycle methods and never receives model credentials.
- Desktop Core stores Conversations, AgentJobs, ToolRuns, and Artifacts in its
  own `desktop-core.db`; a Conversation does not own a process or container.
- The alpha defaults to the model-backed `legacy` runtime. A local OpenHands
  Agent Server can be selected with
  `OPENROSALIND_DESKTOP_AGENT_RUNTIME=openhands`.
- Docker is optional and is reported as a capability, not a startup
  requirement.
- Confirmed Python snippets run through the local Python interpreter when
  Docker is not used. This mode is audited but is not a filesystem or network
  sandbox.

## Development

For a complete Windows setup, build, test, and troubleshooting guide, see
[`WINDOWS_DEVELOPMENT.md`](./WINDOWS_DEVELOPMENT.md).
For the Codex CLI handoff and copy-paste task prompts, see
[`WINDOWS_CODEX.md`](./WINDOWS_CODEX.md).
For macOS development and the `desktop-mac` branch workflow, see
[`MAC_CODEX.md`](./MAC_CODEX.md).
For the shared macOS/Windows local-first Agent, Provider, tool, Docker, security,
and migration architecture, see
[`LOCAL_DESKTOP_ARCHITECTURE.md`](./LOCAL_DESKTOP_ARCHITECTURE.md).
For the versioned Rust-to-Python local Worker contract, see
[`AGENT_WORKER_PROTOCOL.md`](./AGENT_WORKER_PROTOCOL.md).

Prerequisites:

- Python 3.10+
- Node.js 20+
- Rust stable and the platform dependencies required by Tauri 2

From the repository root:

```bash
npm install --prefix desktop
OPENROSALIND_PYTHON=/path/to/python npm run desktop:dev
```

On macOS, use a native Python 3.10+ matching the Node/Rust CPU architecture.
Platform-specific `.app` and `.dmg` commands, Intel/Apple Silicon guidance,
and the signing/notarization contract are documented in
[`MAC_CODEX.md`](./MAC_CODEX.md).

The build prepares a private, bundled Python package directory from
`requirements.txt`; the selected interpreter does not need those packages
installed globally. Model credentials can be supplied through the existing environment variables or in
the application's model settings for the current session. In desktop mode,
temporary Agent-plan credentials are held in memory only and are discarded
when the task completes or the application exits.

## Security Boundary

This alpha does not grant the Agent general access to the user's home
directory. Runtime data is confined to the application-data workspace. Native
project-directory selection and per-command permission prompts are the next
desktop milestone.

The Rust Desktop Core owns the Python process and exposes a read-only
`desktop_core_status` Tauri command. The bootstrap token is never included in
that status payload, persisted to SQLite, or made available to Agent tools.

For browser automation, Debug builds accept
`OPENROSALIND_DESKTOP_TEST_TOKEN` when it contains at least 32 characters.
Release builds ignore this override and always generate a fresh random token.
