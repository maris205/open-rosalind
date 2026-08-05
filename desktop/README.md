# OpenRosalind Desktop Alpha

The desktop alpha wraps the existing OpenRosalind web application in Tauri and
starts the same Python API locally. Skills, task planning, report generation,
message presentation, and biomedical tools remain shared with the web build.

## Current Runtime

- The local API binds only to `127.0.0.1:18765`.
- SQLite data, generated jobs, and Agent workspaces live in the operating
  system's application-data directory.
- Agent jobs use an in-process background queue, so Redis and an RQ worker are
  not required.
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

Prerequisites:

- Python 3.10+
- Node.js 20+
- Rust stable and the platform dependencies required by Tauri 2

From the repository root:

```bash
npm install --prefix desktop
OPENROSALIND_PYTHON=/path/to/python npm run desktop:dev
```

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
