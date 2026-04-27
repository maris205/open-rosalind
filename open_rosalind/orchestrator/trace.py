"""Trace logger: append-only JSONL per session."""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any


class Trace:
    def __init__(self, trace_dir: str | os.PathLike, session_id: str | None = None):
        self.dir = Path(trace_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id or time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        self.path = self.dir / f"{self.session_id}.jsonl"
        self.events: list[dict] = []

    def log(self, kind: str, payload: dict[str, Any]) -> None:
        ev = {"ts": time.time(), "kind": kind, **payload}
        self.events.append(ev)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
