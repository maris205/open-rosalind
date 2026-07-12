# Open-Rosalind Agent Branch

This branch starts the independent Agent version of Open-Rosalind.

Edu remains the beginner-facing learning product. Agent is a research execution product with memory, planning, tool use, evidence tracking, and audit logs.

For product positioning and external workbench references, see:

- `docs/positioning.md`
- `docs/competitive_notes/openscience.md`
- `docs/competitive_notes/biomni.md`

## Product Separation

```text
Open-Rosalind Edu
- learning workflow
- paper reading
- writing scaffolds
- low-risk fixed agents

Open-Rosalind Agent
- project memory
- task planning
- controlled tool execution
- RAG-ready evidence tracking
- audit logs
- reproducible reports
```

## Agent Core

```text
Memory Manager
  -> Project / Evidence / Task memory
Planner
  -> Goal decomposition and approval-ready task plan
Tool Executor
  -> Controlled tools with logs and permission levels
Evidence Layer
  -> Future RAG, references, sequence records, data files
Audit Log
  -> Every tool call, input, output, status, and source locator
Report Builder
  -> Traceable Markdown / DOCX reports
```

## Permission Levels

| Level | Meaning |
| --- | --- |
| 0 | Read-only answer and summarization |
| 1 | Search/read RAG, metadata, references, and uploaded files |
| 2 | Generate reports, tables, figures, and export files |
| 3 | Run local Python/R analysis in a controlled workspace |
| 4 | Modify project files after explicit approval |
| 5 | Publish, push, submit, or external sync; always requires confirmation |

## Non-Negotiable Rules

- Never fabricate DOI, PMID, sequence IDs, datasets, sample sizes, p-values, or tool outputs.
- Every major claim should be connected to evidence or marked unverified.
- Tool execution must produce an audit log entry.
- Raw input data must not be overwritten.
- Dangerous or external actions require explicit user approval.
- Clinical claims remain high-risk and require manual source review.

## Current Scope

This branch includes a first controlled Python executor for short, explicitly approved jobs. It does not yet implement the full RAG database, asynchronous task queue, user authentication, or multi-tenant isolation.

The current Docker execution profile is intentionally restrictive:

- explicit user confirmation is required for every run
- permission level 3 is recorded in the audit log
- no container network
- read-only container root filesystem
- non-root container user
- fixed CPU, memory, process, temporary-storage, and time limits
- input code mounted read-only
- outputs written to a job-specific directory
- code hash, image, limits, logs, exit status, duration, and output hashes are recorded

This synchronous executor is suitable for development and trusted internal testing. Do not expose it as a public anonymous service. Authentication, rate limiting, job queues, per-user storage isolation, retention policies, and stronger container isolation are required before public deployment.

## Development Database and Login

The server uses SQLAlchemy with SQLite by default:

```text
DATABASE_URL=sqlite:////root/rosalind/data/rosalind.db
```

The initial account system supports email/password registration and login without email verification. Passwords are hashed with scrypt. Browser sessions use random HttpOnly, SameSite cookies; only the token hash is stored in the database. Docker jobs, output metadata, and audit records are linked to the authenticated user, and output downloads enforce job ownership.

SQLite uses WAL mode, foreign keys, and a busy timeout. The schema avoids SQLite-specific primary-key and JSON behavior so a later SQLAlchemy migration to MySQL remains practical. Binary uploads and generated outputs stay on disk or future object storage; the database stores metadata, paths, and hashes.

For direct development HTTP access, `ROSALIND_COOKIE_SECURE=0` is required. After routing through HTTPS, set `ROSALIND_COOKIE_SECURE=1` and restart the service.

## Persistent Project Workflow

The first persistent task phase includes:

- user-owned research projects
- structured project memory: fact, evidence, decision, constraint, open question, and conclusion
- Qwen-generated reviewable task plans using existing Agent skills
- explicit plan confirmation before execution
- run-next and run-all controls
- step status, attempts, output, and error persistence
- page-refresh recovery from SQLite
- failed-step retry
- saving completed step output into project memory with source linkage
- automatic recovery of interrupted `running` steps as retryable failures after a server restart

Task execution uses a local Redis queue and an independent RQ Worker. The Web process returns immediately after enqueueing, while each step transition is persisted before and after the model call. Closing or restarting the Web page does not stop the Worker. A per-plan Redis lock prevents duplicate submission. If the Worker itself restarts during a model call, its startup recovery marks the interrupted step as failed, releases the plan lock, and leaves the step available for explicit user retry.

Current background limitations:

- one serial Worker
- no scheduled tasks
- no user-facing cancellation yet
- no automatic retry of failed biomedical steps
- Redis and SQLite run on the same ECS
- Python Docker execution is still a separately confirmed synchronous request

Redis is bound to loopback with protected mode enabled. The ECS deployment enables AOF persistence with `appendfsync everysec`, so a machine-level crash can still lose approximately the most recent second of queue writes. SQLite remains the source of truth for project, plan, step, and memory state; Redis stores queue execution state.

## Product Direction

Agent should be framed as a traceable biomedical research workbench. The core value is not unrestricted autonomy; it is reviewable autonomy with memory, plans, tools, evidence, and audit logs.

The public message should stay distinct from Edu:

- Edu is a guided entry product for students.
- Agent is a project workbench for research execution.
- Future Research can add the unified RAG library, sequence resources, and more advanced controlled analysis workflows.

## Demonstration Examples

Agent demos are available in:

- `examples/agent_task_planner_example.md`
- `examples/agent_memory_update_example.json`
- `examples/agent_tool_audit_example.json`
- `examples/agent_traceable_report_example.md`
- `docs/agent_examples.md`
- `docs/test_examples.md` for end-to-end Web, memory, queue, and Docker validation

These examples are intentionally marked as demonstration outputs. They define expected behavior and output shape, not verified biomedical evidence.
