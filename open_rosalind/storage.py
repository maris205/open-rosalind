"""SQLite storage for users, sessions, tasks, messages.

MVP3.2: Replaces JSONL session store with SQLite for queryability.
JSONL files are still written for trace/audit (in traces/ and task_traces/).
"""
from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at REAL NOT NULL,
    is_anonymous INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tokens (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS sessions (
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
    execution_reason TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    user_goal TEXT,
    status TEXT,
    final_report TEXT,
    n_steps INTEGER,
    created_at REAL NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT,
    card_json TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);

CREATE TABLE IF NOT EXISTS traces (
    trace_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    step_index INTEGER NOT NULL,
    skill TEXT,
    tool TEXT,
    input_json TEXT,
    output_json TEXT,
    status TEXT,
    latency_ms INTEGER,
    created_at REAL NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_traces_session ON traces(session_id, step_index);
CREATE INDEX IF NOT EXISTS idx_traces_user ON traces(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_traces_skill ON traces(skill);
"""


def _hash_password(password: str) -> str:
    """Simple SHA256 + salt. For MVP only."""
    salt = "open-rosalind-mvp3.2"  # TODO: per-user salt for production
    return hashlib.sha256((salt + password).encode()).hexdigest()


def _verify_password(password: str, password_hash: str) -> bool:
    return _hash_password(password) == password_hash


class Storage:
    """SQLite-backed storage for users and sessions."""

    def __init__(self, db_path: str = "./open_rosalind.db"):
        self.db_path = db_path
        self._init_schema()

    def _init_schema(self):
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ===== Users =====

    def create_user(self, email: str, password: str, is_anonymous: bool = False) -> dict:
        user_id = str(uuid.uuid4())
        with self._conn() as c:
            c.execute(
                "INSERT INTO users (user_id, email, password_hash, created_at, is_anonymous) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, email, _hash_password(password), time.time(), int(is_anonymous)),
            )
        return {"user_id": user_id, "email": email, "is_anonymous": is_anonymous}

    def create_anonymous_user(self) -> dict:
        """Create an anonymous user with auto-generated email."""
        anon_id = secrets.token_hex(8)
        return self.create_user(
            email=f"anon_{anon_id}@local",
            password=secrets.token_hex(16),
            is_anonymous=True,
        )

    def get_user_by_email(self, email: str) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: str) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def authenticate(self, email: str, password: str) -> dict | None:
        user = self.get_user_by_email(email)
        if user and _verify_password(password, user["password_hash"]):
            return user
        return None

    # ===== Tokens =====

    def create_token(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        with self._conn() as c:
            c.execute(
                "INSERT INTO tokens (token, user_id, created_at) VALUES (?, ?, ?)",
                (token, user_id, time.time()),
            )
        return token

    def user_from_token(self, token: str) -> dict | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT u.* FROM users u JOIN tokens t ON u.user_id = t.user_id WHERE t.token = ?",
                (token,),
            ).fetchone()
        return dict(row) if row else None

    # ===== Sessions =====

    def save_session(
        self,
        session_id: str,
        user_id: str,
        user_input: str,
        skill: str,
        summary: str,
        confidence: float,
        annotation: dict,
        evidence: dict,
        notes: list,
        execution_mode: str = "single_step",
        execution_reason: str = "",
    ):
        with self._conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO sessions
                (session_id, user_id, user_input, skill, summary, confidence,
                 annotation_json, evidence_json, notes_json,
                 execution_mode, execution_reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id, user_id, user_input, skill, summary, confidence,
                    json.dumps(annotation or {}),
                    json.dumps(evidence or {}),
                    json.dumps(notes or []),
                    execution_mode, execution_reason, time.time(),
                ),
            )

    def list_sessions(self, user_id: str, limit: int = 50) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT session_id, user_input, skill, summary, confidence, "
                "execution_mode, created_at FROM sessions "
                "WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_session(self, session_id: str, user_id: str) -> dict | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM sessions WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["annotation"] = json.loads(d.pop("annotation_json") or "{}")
        d["evidence"] = json.loads(d.pop("evidence_json") or "{}")
        d["notes"] = json.loads(d.pop("notes_json") or "[]")
        return d

    # ===== Messages (chat timeline) =====

    def add_message(self, session_id: str, role: str, content: str, card: dict | None = None):
        with self._conn() as c:
            c.execute(
                "INSERT INTO messages (session_id, role, content, card_json, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, json.dumps(card) if card else None, time.time()),
            )

    def get_messages(self, session_id: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT role, content, card_json, created_at FROM messages "
                "WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["card"] = json.loads(d.pop("card_json")) if d.get("card_json") else None
            out.append(d)
        return out

    # ===== Traces (analytics-friendly) =====

    def save_traces(self, session_id: str, user_id: str, trace_steps: list[dict]):
        """Persist tool-call trace steps for analytics queries.

        trace_steps shape (from agent's structured trace):
            [{"skill": str, "input": dict, "output": dict, "status": str, "latency_ms": int}, ...]
        """
        if not trace_steps:
            return
        rows = []
        for i, step in enumerate(trace_steps):
            rows.append((
                session_id,
                user_id,
                i,
                step.get("skill"),
                step.get("tool") or step.get("skill"),
                json.dumps(step.get("input"), ensure_ascii=False) if step.get("input") is not None else None,
                json.dumps(step.get("output"), ensure_ascii=False) if step.get("output") is not None else None,
                step.get("status"),
                step.get("latency_ms"),
                time.time(),
            ))
        with self._conn() as c:
            c.executemany(
                "INSERT INTO traces (session_id, user_id, step_index, skill, tool, "
                "input_json, output_json, status, latency_ms, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )

    def get_traces(self, session_id: str) -> list[dict]:
        """Load all trace steps for a session, ordered by step index."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT step_index, skill, tool, input_json, output_json, "
                "status, latency_ms, created_at FROM traces "
                "WHERE session_id = ? ORDER BY step_index ASC",
                (session_id,),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["input"] = json.loads(d.pop("input_json")) if d.get("input_json") else None
            d["output"] = json.loads(d.pop("output_json")) if d.get("output_json") else None
            out.append(d)
        return out

    def stats(self, user_id: str | None = None) -> dict:
        """Return basic analytics counters. Useful for admin dashboards."""
        with self._conn() as c:
            if user_id:
                where = "WHERE user_id = ?"
                args: tuple = (user_id,)
            else:
                where = ""
                args = ()
            n_sessions = c.execute(f"SELECT COUNT(*) FROM sessions {where}", args).fetchone()[0]
            n_traces = c.execute(f"SELECT COUNT(*) FROM traces {where}", args).fetchone()[0]
            n_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            top_skills = c.execute(
                f"SELECT skill, COUNT(*) AS n FROM traces {where} "
                "GROUP BY skill ORDER BY n DESC LIMIT 10",
                args,
            ).fetchall()
            avg_latency = c.execute(
                f"SELECT skill, AVG(latency_ms) AS avg_ms FROM traces {where} "
                "WHERE latency_ms IS NOT NULL GROUP BY skill",
                args,
            ).fetchall() if user_id else c.execute(
                "SELECT skill, AVG(latency_ms) AS avg_ms FROM traces "
                "WHERE latency_ms IS NOT NULL GROUP BY skill"
            ).fetchall()
        return {
            "n_users": n_users,
            "n_sessions": n_sessions,
            "n_traces": n_traces,
            "top_skills": [dict(r) for r in top_skills],
            "avg_latency_ms_by_skill": [dict(r) for r in avg_latency],
        }
