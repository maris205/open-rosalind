# MVP3.2: Chat UI + Auth + SQLite

> Chat-style interface, auto execution mode, simple email auth, SQLite storage

---

## Overview

MVP3.2 transforms Open-Rosalind from a "form-based tool" into a "scientific chat assistant" while keeping the structured evidence/trace cards that make it credible.

**Per `develop/mvp3.2.md` + user feedback**:
- Chat-style UI (not form-based)
- Auto execution mode (no user-visible single/multi-step selector)
- Email-only registration (no email verification, no OAuth)
- SQLite for sessions/users (replace JSONL for queryability)

---

## Architecture Comparison

| Aspect | MVP3.1 | MVP3.2 |
|---|---|---|
| **UI** | Form (input box → result panel) | Chat timeline (messages + cards) |
| **Mode selector** | Visible (Single / Multi-step) | Hidden (auto-detected) |
| **Auth** | None (anonymous) | Email signup + login |
| **Storage** | JSONL files | SQLite + JSONL audit log |
| **Context** | session-based follow-up | session context with entity tracking |

---

## Tasks

### Task 1: Auto execution mode

Replace user-facing "Single-step / Multi-step" with auto-detection:

```python
def select_mode(user_input: str) -> tuple[str, str]:
    """
    Returns: (mode, reason)
    
    Heuristic:
    - "find papers AND ..." → harness (multi-step)
    - "analyze AND ..." → harness if 2+ verbs
    - sequence/accession only → single_step
    - default → single_step
    """
    if any(kw in user_input.lower() for kw in ["and find papers", "and look up", "then "]):
        return "harness", "requires multiple skills"
    return "single_step", "single skill suffices"
```

API response adds:
```json
{
  "execution_mode": "harness",
  "execution_reason": "requires literature + annotation"
}
```

### Task 2: Chat UI (React)

Layout:
```
┌─────────────┬──────────────────────────────────┐
│  Sessions   │  Chat Timeline                   │
│  (sidebar)  │  ┌────────────────────────────┐  │
│             │  │ User: Analyze BRCA1...     │  │
│             │  └────────────────────────────┘  │
│             │  ┌────────────────────────────┐  │
│             │  │ Assistant:                 │  │
│             │  │  ┌──────────┐              │  │
│             │  │  │ Summary  │              │  │
│             │  │  │ Evidence │              │  │
│             │  │  │ Trace ▼  │              │  │
│             │  │  │ Conf 0.9 │              │  │
│             │  │  └──────────┘              │  │
│             │  └────────────────────────────┘  │
│             │  ┌────────────────────────────┐  │
│             │  │ [Input box]      [Send]    │  │
│             │  └────────────────────────────┘  │
└─────────────┴──────────────────────────────────┘
```

Each session = list of message turns:
```typescript
interface MessageTurn {
  role: "user" | "assistant"
  content: string  // user input or assistant summary
  card?: {
    summary, annotation, confidence, notes,
    evidence, trace_steps, execution_mode
  }
  timestamp: number
}
```

### Task 3: Session context (entity tracking)

Within a session, maintain entity context:
```python
session_context = {
  "last_protein": "BRCA1",
  "last_accession": "P38398",
  "last_pmids": [...],
}
```

Follow-up like "find related papers" auto-injects context.

### Task 4: Simple email auth (NO email verification, NO OAuth)

Per user request: keep it minimal.

**Endpoints**:
- `POST /api/auth/signup`: `{email, password}` → creates user, returns token
- `POST /api/auth/login`: `{email, password}` → returns token
- `GET /api/auth/me`: requires `Authorization: Bearer <token>` → returns user

**Storage**: SQLite `users` table:
```sql
CREATE TABLE users (
  user_id TEXT PRIMARY KEY,    -- uuid
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,  -- bcrypt
  created_at REAL,
  is_anonymous INTEGER DEFAULT 0
);
```

**Anonymous mode**: if no token, create anonymous user (auto-generated email like `anon_<uuid>@local`). No friction for first-time visitors.

**No email verification**: just hash password, set token, done.

### Task 5: SQLite storage

Replace JSONL session store with SQLite (keep JSONL as audit log):

```sql
CREATE TABLE sessions (
  session_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  user_input TEXT,
  skill TEXT,
  summary TEXT,
  confidence REAL,
  annotation_json TEXT,
  evidence_json TEXT,
  notes_json TEXT,
  execution_mode TEXT,
  created_at REAL,
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);
CREATE INDEX idx_sessions_user ON sessions(user_id, created_at DESC);

CREATE TABLE tasks (
  task_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  user_goal TEXT,
  status TEXT,
  final_report TEXT,
  n_steps INTEGER,
  created_at REAL
);

CREATE TABLE messages (
  message_id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,         -- user | assistant
  content TEXT,
  card_json TEXT,
  created_at REAL,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
```

**Migration**: New install → SQLite only. JSONL still written for trace/audit.

---

## Implementation Order

1. ✅ **SQLite storage** (foundation for auth + sessions)
2. ✅ **Email auth** (simple: signup/login/me)
3. ✅ **Auto execution mode** (backend logic)
4. ✅ **Chat UI** (React refactor)
5. ✅ **Session context** (entity tracking in chat)

---

## What MVP3.2 Does NOT Do

- ❌ Email verification (per user request)
- ❌ OAuth (GitHub/Google) — needs API key registration, save for later
- ❌ Magic link (requires email server)
- ❌ Long-term memory across sessions
- ❌ User roles / permissions
- ❌ Billing / quotas

---

## Success Criteria

1. ✅ User can sign up with email + password (no verification)
2. ✅ Anonymous users can still try the demo
3. ✅ Chat UI shows user messages + AI cards
4. ✅ No "Single-step / Multi-step" toggle visible
5. ✅ Backend auto-selects mode based on input
6. ✅ Sessions persist in SQLite (queryable by user)
7. ✅ Follow-up questions reuse session context automatically
8. ✅ All BioBench v0/v1/v0.3 still pass
