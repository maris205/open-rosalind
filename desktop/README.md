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
- A separate, long-lived local Agent Worker starts outside Docker and uses a
  versioned JSON-RPC protocol over stdio. Protocol v4 supports AgentJob start,
  status polling, cooperative cancellation, structured progress, credential-
  free model requests, and bounded low-risk Tool Contract requests. The Worker
  still has no direct model, credential, Shell, filesystem, network, Docker, or
  tool access.
- Desktop Core stores UI chats and messages, Conversations, AgentJobs, ordered
  AgentJob events, ToolRuns, and Artifacts in its own `desktop-core.db`; a
  Conversation does not own a process or container. Chat snapshots are replaced
  atomically and isolated by the signed-in local user. Unfinished jobs recover
  as `interrupted` after an application restart.
- Desktop Core verifies SQLite integrity before and after transactional schema
  migration. It creates WAL-safe online snapshots at startup (at most once per
  six hours), after changed data on a clean shutdown, and on demand from
  Settings. Every snapshot is opened read-only and fully verified before it is
  finalized; only the five newest app-managed snapshots are rotated. A failed
  integrity check preserves the original database and reports the backup
  directory instead of silently overwriting user data.
- Schema v5 migrates legacy macOS WebKit `localStorage` chat databases on first
  launch. It merges duplicate chat IDs using the newest copy, then makes Desktop
  Core SQLite the authoritative store. The current-origin browser copy remains
  only as a recovery fallback and is no longer the desktop source of truth.
- Provider Profiles store only non-sensitive metadata in `desktop-core.db`.
  Model API Keys are saved through the operating system credential vault
  (macOS Keychain or Windows Credential Manager) and are never returned to the
  Web UI or local Python API.
- Ordinary desktop model requests are sent directly from the Rust Provider
  Broker to an OpenAI-compatible HTTPS endpoint. The broker supports streaming,
  cooperative cancellation, timeouts, bounded requests, and sanitized errors;
  these calls do not pass through an OpenRosalind model service.
- Desktop Core includes a Tool Contract v1 registry and durable ToolRun audit
  records. The first `text.statistics` Native Tool is low risk and has no
  filesystem, network, or Secret permissions. `python.run` uses a per-run
  approval state machine and records its critical host filesystem/network
  snapshot before execution. Rust Tool Manager launches it with a fixed Python
  interpreter, isolated run directories, an environment allowlist, a
  cross-platform process group, timeout/cancellation, and bounded logs/output;
  the Agent Worker cannot approve or start it.
- Native Python output files are indexed in SQLite as immutable Artifacts with
  relative paths, sizes, and SHA-256 digests. The shared WebView receives only
  Artifact IDs. Desktop Core revalidates the path, size, and digest before a
  bounded UTF-8 preview, revealing the file in Finder/Explorer, or exporting it
  through a native Save dialog. The WebView cannot choose an arbitrary export
  path directly.
- The alpha defaults to the model-backed `legacy` runtime. A local OpenHands
  Agent Server can be selected with
  `OPENROSALIND_DESKTOP_AGENT_RUNTIME=openhands`.
- Docker is optional and is reported as a capability, not a startup
  requirement.
- macOS release bundles contain a relocatable, architecture-matched CPython
  3.11 runtime and hash-locked Python dependencies. Release builds ignore
  `OPENROSALIND_PYTHON` and fail closed if the signed bundle is incomplete, so
  an installed app no longer depends on Homebrew, Xcode Python, or a user
  virtual environment. Development mode may still use an explicitly selected
  local Python.
- The first optional Container Executor runs approved Python in a pinned,
  multi-architecture Docker Official Image. It uses no network, a read-only
  root filesystem, a numeric non-root user, no Linux capabilities, no-new-
  privileges, bounded CPU/memory/PIDs/time/output, and only per-run input/output
  mounts. Image preparation is explicit and a missing Docker daemon never
  blocks the main Agent or native tools.
- Confirmed desktop Python snippets run directly through Rust Tool Manager and
  no longer round-trip through the local Web API. This mode is audited and
  bounded, but it is intentionally not a filesystem or network sandbox.

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
For the cross-platform tool extension and permission contract, see
[`TOOL_CONTRACT.md`](./TOOL_CONTRACT.md).

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

Development prepares a private Python package directory from `requirements.txt`.
macOS packaging instead downloads the exact CPython artifact declared in
`python-runtime-manifest.json`, verifies its SHA-256 digest, and installs only
hash-locked wheels from `requirements-runtime.lock` into that runtime. The
generated runtimes are ignored by Git and the downloaded archive is cached in
the user's Library cache. In desktop mode, save an OpenAI-compatible Base URL,
model, and API Key in Settings. The Base URL and model are local SQLite
metadata; the API Key is written directly to the system credential vault. Web
mode continues to support the existing environment-variable and session
settings.

The desktop research assistant now runs as a persisted AgentJob. The Worker
submits bounded model and automatic-tool requests to Desktop Core. Desktop Core
resolves the system credential, performs HTTPS calls, validates Tool Contracts,
executes the three low-risk tools, and returns sanitized results. Protocol v4
supports up to four model/tool rounds for text statistics and authorized project
file listing/preview. High-risk Python and Docker remain in the explicit user
approval flow.

Desktop chat persistence is separate from execution Conversations so replacing
or clearing UI history cannot cascade-delete AgentJob audit records. Desktop IPC
validates chat/message IDs, roles, size limits, active-chat ownership, and writes
the complete snapshot in one SQLite transaction. Browser automation covers a
save-and-reload cycle in addition to Rust round-trip, isolation, migration, and
rollback tests.

## Security Boundary

This alpha does not grant the Agent general access to the user's home
directory. Runtime data is confined to the application-data workspace. A user
can now bind one explicitly selected local directory to a research project from
the native folder picker, reveal it in Finder or File Explorer, and revoke the
authorization. The WebView cannot submit an arbitrary path, filesystem roots
and the entire home directory are rejected, and a directory cannot be bound to
two projects. The first project-aware Tool Contracts can list non-sensitive
files and preview allowlisted UTF-8 text through relative paths. They do not
grant Python, the Agent Worker, or write-capable tools access to the directory.

The Rust Desktop Core owns the Python process and exposes a restricted set of
Tauri commands to the authenticated loopback UI. The bootstrap token is never
included in status payloads, persisted to SQLite, or made available to Agent
tools. Navigation is limited to the exact per-launch loopback origin and the
desktop page uses a restrictive Content Security Policy.

For browser automation, Debug builds accept
`OPENROSALIND_DESKTOP_TEST_TOKEN` when it contains at least 32 characters.
Release builds ignore this override and always generate a fresh random token.
