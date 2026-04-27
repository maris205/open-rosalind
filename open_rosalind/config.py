from __future__ import annotations

import os
from pathlib import Path

import yaml


def load_config(path: str | os.PathLike | None = None) -> dict:
    if path is None:
        path = Path(__file__).resolve().parent.parent / "configs" / "default.yaml"
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    _load_dotenv()
    return cfg


def _load_dotenv() -> None:
    root = Path(__file__).resolve().parent.parent
    for name in (".env", ".env.local"):
        p = root / name
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
