"""NCBI BLAST Common URL API client."""
from __future__ import annotations

import io
import json
import os
import re
import time
import zipfile
from typing import Any, Callable

import requests

from ._http import make_session
from .base import ToolSpec

BLAST_URL = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"
DEFAULT_TOOL = "open-rosalind"
MIN_REQUEST_INTERVAL_SEC = 10
MIN_POLL_INTERVAL_SEC = 60

RID_RE = re.compile(r"^\s*RID\s*=\s*(\S+)", re.MULTILINE)
RTOE_RE = re.compile(r"^\s*RTOE\s*=\s*(\d+)", re.MULTILINE)
STATUS_RE = re.compile(r"Status=(WAITING|READY|FAILED|UNKNOWN)")

VALID_PROGRAMS = {"blastn", "blastp", "blastx", "tblastn", "tblastx"}


class RequestThrottle:
    def __init__(
        self,
        min_interval_sec: int = MIN_REQUEST_INTERVAL_SEC,
        sleep_fn: Callable[[float], None] = time.sleep,
        clock_fn: Callable[[], float] = time.time,
    ) -> None:
        self.min_interval_sec = min_interval_sec
        self.sleep_fn = sleep_fn
        self.clock_fn = clock_fn
        self.last_request_ts: float | None = None

    def request(self, session: requests.Session, method: str, **kwargs: Any) -> requests.Response:
        if self.last_request_ts is not None:
            remaining = self.min_interval_sec - (self.clock_fn() - self.last_request_ts)
            if remaining > 0:
                self.sleep_fn(remaining)
        response = session.request(method, BLAST_URL, **kwargs)
        self.last_request_ts = self.clock_fn()
        response.raise_for_status()
        return response


def _blast_session(tool: str, email: str) -> requests.Session:
    session = make_session()
    session.headers["User-Agent"] = f"open-rosalind/1.0 tool={tool} email={email}"
    return session


def _summarize_json2_payload(data: dict[str, Any], max_queries: int, max_hits: int) -> dict[str, Any]:
    reports = data.get("BlastOutput2")
    if isinstance(reports, dict):
        reports = [reports]
    if not isinstance(reports, list):
        raise ValueError("BLAST JSON2 payload did not include BlastOutput2")

    summaries: list[dict[str, Any]] = []
    has_hits = False
    for index, report in enumerate(reports[:max_queries], start=1):
        if not isinstance(report, dict):
            continue
        search = (((report.get("report") or {}).get("results") or {}).get("search") or {})
        if not isinstance(search, dict):
            continue
        query_title = search.get("query_title") or search.get("query_id") or f"query_{index}"
        hits = search.get("hits") or []
        top_hits = []
        for rank, hit in enumerate(hits[:max_hits], start=1):
            if not isinstance(hit, dict):
                continue
            descriptions = hit.get("description") or []
            desc = descriptions[0] if descriptions and isinstance(descriptions[0], dict) else {}
            hsps = hit.get("hsps") or []
            hsp = hsps[0] if hsps and isinstance(hsps[0], dict) else {}
            top_hits.append(
                {
                    "rank": rank,
                    "accession": desc.get("accession") or desc.get("id"),
                    "title": desc.get("title"),
                    "evalue": hsp.get("evalue"),
                    "bit_score": hsp.get("bit_score"),
                }
            )
        hit_count_available = len(hits) if isinstance(hits, list) else 0
        has_hits = has_hits or hit_count_available > 0
        summaries.append(
            {
                "query_title": query_title,
                "hit_count_returned": len(top_hits),
                "hit_count_available": hit_count_available,
                "truncated": len(top_hits) < hit_count_available,
                "top_hits": top_hits,
            }
        )

    return {
        "query_count_returned": len(summaries),
        "query_count_available": len(reports),
        "query_summaries_truncated": len(summaries) < len(reports),
        "query_summaries": summaries,
        "has_hits": has_hits,
    }


def _load_json_member(zip_file: zipfile.ZipFile, member_name: str) -> dict[str, Any]:
    payload = json.loads(zip_file.read(member_name).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"BLAST archive member {member_name!r} was not a JSON object")
    return payload


def _extract_json2_payload(response: requests.Response) -> dict[str, Any]:
    content_type = (response.headers.get("content-type") or "").lower()
    raw_bytes = response.content
    if content_type.startswith("application/zip") or raw_bytes.startswith(b"PK\x03\x04"):
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zip_file:
            json_members = [name for name in zip_file.namelist() if name.lower().endswith(".json")]
            if not json_members:
                raise ValueError("BLAST JSON2 archive did not contain JSON members")

            payloads = [
                _load_json_member(zip_file, member_name)
                for member_name in json_members
                if "BlastOutput2" in _load_json_member(zip_file, member_name)
            ]
            if not payloads:
                raise ValueError("BLAST JSON2 archive did not contain a BlastOutput2 payload")
            if len(payloads) == 1:
                return payloads[0]

            merged = dict(payloads[0])
            merged_reports: list[Any] = []
            for payload in payloads:
                reports = payload.get("BlastOutput2")
                if isinstance(reports, dict):
                    merged_reports.append(reports)
                elif isinstance(reports, list):
                    merged_reports.extend(reports)
            merged["BlastOutput2"] = merged_reports
            return merged

    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("BLAST JSON2 response was not a JSON object")
    return data


def _submit_search(
    session: requests.Session,
    throttle: RequestThrottle,
    program: str,
    database: str,
    query_fasta: str,
    hitlist_size: int,
    tool: str,
    email: str,
) -> tuple[str, int]:
    response = throttle.request(
        session,
        "POST",
        data={
            "CMD": "Put",
            "PROGRAM": program,
            "DATABASE": database,
            "QUERY": query_fasta,
            "FORMAT_TYPE": "Text",
            "HITLIST_SIZE": hitlist_size,
            "tool": tool,
            "email": email,
        },
        timeout=60,
    )
    rid_match = RID_RE.search(response.text)
    rtoe_match = RTOE_RE.search(response.text)
    if not rid_match:
        raise ValueError("BLAST submit response did not include an RID")
    return rid_match.group(1), int(rtoe_match.group(1)) if rtoe_match else MIN_REQUEST_INTERVAL_SEC


def _search_info(
    session: requests.Session,
    throttle: RequestThrottle,
    rid: str,
    tool: str,
    email: str,
) -> tuple[str, bool]:
    response = throttle.request(
        session,
        "GET",
        params={
            "CMD": "Get",
            "FORMAT_OBJECT": "SearchInfo",
            "RID": rid,
            "tool": tool,
            "email": email,
        },
        timeout=30,
    )
    status_match = STATUS_RE.search(response.text)
    if not status_match:
        raise ValueError("BLAST SearchInfo response did not include a recognizable status")
    return status_match.group(1), "ThereAreHits=yes" in response.text


def _fetch_ready_result(
    session: requests.Session,
    throttle: RequestThrottle,
    rid: str,
    tool: str,
    email: str,
    max_queries: int,
    max_hits: int,
) -> dict[str, Any]:
    response = throttle.request(
        session,
        "GET",
        params={
            "CMD": "Get",
            "RID": rid,
            "FORMAT_TYPE": "JSON2",
            "tool": tool,
            "email": email,
        },
        timeout=60,
    )
    data = _extract_json2_payload(response)
    return _summarize_json2_payload(data, max_queries=max_queries, max_hits=max_hits)


def run_search(
    program: str,
    database: str,
    query_fasta: str,
    email: str | None = None,
    max_hits: int = 5,
    max_queries: int = 5,
    hitlist_size: int = 50,
    wait_timeout_sec: int = 900,
    tool: str | None = None,
    *,
    session: requests.Session | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    clock_fn: Callable[[], float] = time.time,
) -> dict[str, Any]:
    """Submit, poll, and summarize an NCBI BLAST search."""
    clean_program = program.strip().lower()
    clean_database = database.strip()
    clean_query = query_fasta.strip()
    clean_email = (email or os.environ.get("NCBI_EMAIL") or "").strip()
    tool_name = (tool or os.environ.get("NCBI_TOOL") or DEFAULT_TOOL).strip() or DEFAULT_TOOL

    if clean_program not in VALID_PROGRAMS:
        raise ValueError("program must be one of blastn, blastp, blastx, tblastn, tblastx")
    if not clean_database:
        raise ValueError("database is required")
    if not clean_query:
        raise ValueError("query_fasta is required")
    if not clean_email:
        raise ValueError("email is required for NCBI BLAST or via NCBI_EMAIL")

    local_session = session or _blast_session(tool_name, clean_email)
    throttle = RequestThrottle(sleep_fn=sleep_fn, clock_fn=clock_fn)
    try:
        rid, rtoe_seconds = _submit_search(
            local_session,
            throttle,
            clean_program,
            clean_database,
            clean_query,
            max(1, int(hitlist_size)),
            tool_name,
            clean_email,
        )
        deadline = clock_fn() + max(1, int(wait_timeout_sec))
        initial_wait = max(rtoe_seconds, MIN_REQUEST_INTERVAL_SEC)
        if clock_fn() + initial_wait > deadline:
            return {
                "program": clean_program,
                "database": clean_database,
                "rid": rid,
                "rtoe_seconds": rtoe_seconds,
                "status": "WAITING",
                "has_hits": False,
                "query_count_returned": 0,
                "query_count_available": 0,
                "query_summaries_truncated": False,
                "query_summaries": [],
            }

        sleep_fn(initial_wait)
        while True:
            status, has_hits = _search_info(local_session, throttle, rid, tool_name, clean_email)
            if status == "READY":
                if not has_hits:
                    return {
                        "program": clean_program,
                        "database": clean_database,
                        "rid": rid,
                        "rtoe_seconds": rtoe_seconds,
                        "status": "READY",
                        "has_hits": False,
                        "query_count_returned": 0,
                        "query_count_available": 0,
                        "query_summaries_truncated": False,
                        "query_summaries": [],
                    }
                summary = _fetch_ready_result(
                    local_session,
                    throttle,
                    rid,
                    tool_name,
                    clean_email,
                    max_queries=max(1, int(max_queries)),
                    max_hits=max(1, int(max_hits)),
                )
                return {
                    "program": clean_program,
                    "database": clean_database,
                    "rid": rid,
                    "rtoe_seconds": rtoe_seconds,
                    "status": "READY",
                    **summary,
                }
            if status == "FAILED":
                raise ValueError(f"BLAST job {rid} reported FAILED")
            if status == "UNKNOWN":
                raise ValueError(f"BLAST job {rid} reported UNKNOWN or expired")

            remaining = deadline - clock_fn()
            if remaining <= MIN_POLL_INTERVAL_SEC:
                return {
                    "program": clean_program,
                    "database": clean_database,
                    "rid": rid,
                    "rtoe_seconds": rtoe_seconds,
                    "status": "WAITING",
                    "has_hits": False,
                    "query_count_returned": 0,
                    "query_count_available": 0,
                    "query_summaries_truncated": False,
                    "query_summaries": [],
                }
            sleep_fn(MIN_POLL_INTERVAL_SEC)
    finally:
        if session is None:
            local_session.close()


RUN_SEARCH_SPEC = ToolSpec(
    name="ncbi_blast.run_search",
    description="Submit, poll, and summarize an NCBI BLAST search with top-hit JSON2 results.",
    input_schema={
        "type": "object",
        "properties": {
            "program": {"type": "string"},
            "database": {"type": "string"},
            "query_fasta": {"type": "string"},
            "email": {"type": "string"},
            "max_hits": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
            "max_queries": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
            "hitlist_size": {"type": "integer", "default": 50, "minimum": 1, "maximum": 500},
            "wait_timeout_sec": {"type": "integer", "default": 900, "minimum": 1, "maximum": 3600},
            "tool": {"type": "string"},
        },
        "required": ["program", "database", "query_fasta"],
    },
    output_schema={"type": "object"},
    handler=run_search,
)
