"""SessionMemory — MVP2 Task 3.

JSONL-backed session store. Each session writes one `.jsonl` file under
`sessions/` with a stream of events:
  - start (user_input, mode)
  - skill_call (skill, payload)
  - skill_result (evidence, annotation, confidence, notes)
  - summary (text)

The agent writes these events as it runs. The API exposes:
  - GET /api/sessions       → list recent sessions
  - GET /api/sessions/{id}  → full session replay

This enables:
  - Task 2 (AgentRunner) follow-up: "再查一下这个蛋白的文献" can reload
    the last session's evidence as context.
  - Task 4 (session sidebar UI): the sidebar lists past sessions and lets
    the user click to reload.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class SessionEvent:
    kind: str
    ts: float
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"kind": self.kind, "ts": self.ts, **self.data}

    @staticmethod
    def from_dict(d: dict) -> SessionEvent:
        return SessionEvent(kind=d["kind"], ts=d["ts"], data={k: v for k, v in d.items() if k not in ("kind", "ts")})


class SessionStore:
    """Append-only JSONL session log."""

    def __init__(self, base_dir: str = "./sessions"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        return self.base_dir / f"{session_id}.jsonl"

    def write_event(self, session_id: str, kind: str, **data):
        """Append one event to the session log."""
        ev = SessionEvent(kind=kind, ts=datetime.now(timezone.utc).timestamp(), data=data)
        with self._path(session_id).open("a") as f:
            f.write(json.dumps(ev.to_dict(), ensure_ascii=False, default=str) + "\n")

    def read_session(self, session_id: str) -> list[SessionEvent]:
        """Load all events for a session."""
        p = self._path(session_id)
        if not p.exists():
            return []
        events = []
        for line in p.read_text().splitlines():
            if line.strip():
                events.append(SessionEvent.from_dict(json.loads(line)))
        return events

    def list_sessions(self, limit: int = 50) -> list[dict]:
        """List recent sessions (newest first), returning compact metadata."""
        files = sorted(self.base_dir.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
        out = []
        for f in files[:limit]:
            session_id = f.stem
            events = self.read_session(session_id)
            if not events:
                continue
            start_ev = next((e for e in events if e.kind == "start"), None)
            summary_ev = next((e for e in reversed(events) if e.kind == "summary"), None)
            out.append({
                "session_id": session_id,
                "created_at": events[0].ts if events else None,
                "user_input": start_ev.data.get("user_input") if start_ev else None,
                "summary_preview": (summary_ev.data.get("text") or "")[:120] if summary_ev else None,
                "n_events": len(events),
            })
        return out

    def get_last_evidence(self, session_id: str) -> dict | None:
        """Extract the most recent skill_result evidence for follow-up queries."""
        events = self.read_session(session_id)
        for ev in reversed(events):
            if ev.kind == "skill_result" and ev.data.get("evidence"):
                return ev.data["evidence"]
        return None
