"""Shared HTTP helpers.

UniProt and NCBI E-utilities are directly reachable from CN (verified at runtime
~1-2s). When OPEN_ROSALIND_BIODB_BYPASS_PROXY=1 (default), bio-DB requests
ignore HTTP(S)_PROXY env vars so a flaky overseas proxy can't slow them down.
A single transparent retry is added on connect/read timeouts.
"""
from __future__ import annotations

import os
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def _bypass_proxy() -> bool:
    return os.environ.get("OPEN_ROSALIND_BIODB_BYPASS_PROXY", "1") == "1"


def make_session() -> requests.Session:
    s = requests.Session()
    if _bypass_proxy():
        s.trust_env = False
        s.proxies = {}
    retry = Retry(
        total=2,
        backoff_factor=0.6,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s


def get_json(url: str, params: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    s = make_session()
    r = s.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()
