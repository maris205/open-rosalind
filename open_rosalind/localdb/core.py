"""SQLite-backed local bio database for high-value seeded records."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


DEFAULT_DB_PATH = Path("./open_rosalind_local.db")
DEFAULT_SEED_PATH = Path(__file__).resolve().parent / "seeds" / "uniprot_minimal.json"
_ACCESSION_RE = re.compile(
    r"\b([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})\b"
)
_GENE_EXACT_RE = re.compile(r'gene_exact:(?:"([^"]+)"|([^\s]+))', re.IGNORECASE)
_ORGANISM_RE = re.compile(r'organism_name:(?:"([^"]+)"|([^\s]+(?:\s+[^\s]+)*))', re.IGNORECASE)
_STOPWORDS = {
    "and", "or", "the", "a", "an", "of", "for", "in", "on", "to", "with", "by", "from",
    "what", "is", "are", "was", "were", "be", "been", "being", "do", "does", "did",
    "describe", "explain", "tell", "me", "about", "show", "find", "search", "lookup",
    "function", "role", "protein", "gene", "human", "humans", "homo", "sapiens",
}


def _env_flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").strip().lower()).strip()


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[A-Za-z0-9]+", text.lower()) if token not in _STOPWORDS]


def _truncate(text: str | None, limit: int = 600) -> str | None:
    if text is None:
        return None
    value = str(text)
    return value[:limit]


@dataclass(frozen=True, slots=True)
class LocalBioDBConfig:
    db_path: Path
    seed_path: Path
    offline: bool = False

    @classmethod
    def from_env(
        cls,
        db_path: str | os.PathLike[str] | None = None,
        seed_path: str | os.PathLike[str] | None = None,
        offline: bool | None = None,
    ) -> "LocalBioDBConfig":
        resolved_db_path = db_path or os.environ.get("OPEN_ROSALIND_LOCALDB_PATH") or DEFAULT_DB_PATH
        return cls(
            db_path=Path(resolved_db_path),
            seed_path=Path(seed_path or DEFAULT_SEED_PATH),
            offline=_env_flag("OPEN_ROSALIND_OFFLINE") if offline is None else offline,
        )


class LocalBioDB:
    """Small SQLite database for local-first bio lookups."""

    def __init__(
        self,
        db_path: str | os.PathLike[str] | None = None,
        seed_path: str | os.PathLike[str] | None = None,
        offline: bool | None = None,
    ):
        self.config = LocalBioDBConfig.from_env(db_path=db_path, seed_path=seed_path, offline=offline)
        self.db_path = self.config.db_path
        self.seed_path = self.config.seed_path
        self.offline = self.config.offline
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self, force_seed: bool = False) -> None:
        with self._connect() as conn:
            conn.executescript(self._schema())
            if force_seed or not self._is_seeded(conn):
                self._seed(conn)

    @staticmethod
    def _schema() -> str:
        return """
        CREATE TABLE IF NOT EXISTS localdb_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS localdb_datasets (
            dataset_name TEXT PRIMARY KEY,
            dataset_version TEXT NOT NULL,
            source TEXT,
            source_url TEXT,
            installed_at REAL NOT NULL,
            record_count INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS uniprot_entries (
            accession TEXT PRIMARY KEY,
            entry_id TEXT,
            name TEXT,
            organism TEXT,
            length INTEGER,
            sequence TEXT,
            function TEXT,
            reviewed INTEGER DEFAULT 1,
            source TEXT,
            source_url TEXT
        );

        CREATE TABLE IF NOT EXISTS uniprot_entry_genes (
            accession TEXT NOT NULL,
            gene_symbol TEXT NOT NULL,
            FOREIGN KEY (accession) REFERENCES uniprot_entries(accession) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_uniprot_entry_genes_gene
            ON uniprot_entry_genes(gene_symbol);
        CREATE INDEX IF NOT EXISTS idx_uniprot_entries_name
            ON uniprot_entries(name);
        CREATE INDEX IF NOT EXISTS idx_uniprot_entries_organism
            ON uniprot_entries(organism);
        """

    def _is_seeded(self, conn: sqlite3.Connection) -> bool:
        row = conn.execute(
            "SELECT value FROM localdb_metadata WHERE key = ?",
            ("seed_version",),
        ).fetchone()
        if not row:
            return False
        if not self.seed_path.exists():
            return True
        try:
            seed = json.loads(self.seed_path.read_text(encoding="utf-8"))
        except Exception:
            return False
        return row["value"] == str(seed.get("version") or "")

    def _seed(self, conn: sqlite3.Connection) -> None:
        if not self.seed_path.exists():
            conn.execute("DELETE FROM localdb_datasets")
            conn.execute("DELETE FROM localdb_metadata")
            conn.execute("DELETE FROM uniprot_entry_genes")
            conn.execute("DELETE FROM uniprot_entries")
            conn.execute(
                "INSERT OR REPLACE INTO localdb_metadata (key, value) VALUES (?, ?)",
                ("seed_state", "missing"),
            )
            return

        seed = json.loads(self.seed_path.read_text(encoding="utf-8"))
        records = list(seed.get("records") or [])
        dataset_name = str(seed.get("dataset") or "uniprot_minimal")
        dataset_version = str(seed.get("version") or "0")
        source = str(seed.get("source") or "UniProtKB reviewed seed")
        source_url = str(seed.get("source_url") or "https://rest.uniprot.org")

        conn.execute("DELETE FROM localdb_datasets")
        conn.execute("DELETE FROM localdb_metadata")
        conn.execute("DELETE FROM uniprot_entry_genes")
        conn.execute("DELETE FROM uniprot_entries")

        conn.execute(
            """
            INSERT OR REPLACE INTO localdb_datasets
            (dataset_name, dataset_version, source, source_url, installed_at, record_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (dataset_name, dataset_version, source, source_url, time.time(), len(records)),
        )
        metadata = {
            "seed_dataset": dataset_name,
            "seed_version": dataset_version,
            "seed_source": source,
            "seed_source_url": source_url,
            "seed_records": str(len(records)),
        }
        for key, value in metadata.items():
            conn.execute(
                "INSERT OR REPLACE INTO localdb_metadata (key, value) VALUES (?, ?)",
                (key, value),
            )

        for record in records:
            accession = str(record["accession"])
            conn.execute(
                """
                INSERT OR REPLACE INTO uniprot_entries
                (accession, entry_id, name, organism, length, sequence, function, reviewed, source, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    accession,
                    record.get("id"),
                    record.get("name"),
                    record.get("organism"),
                    record.get("length"),
                    record.get("sequence"),
                    record.get("function"),
                    int(bool(record.get("reviewed", True))),
                    record.get("source"),
                    record.get("source_url"),
                ),
            )
            for gene in record.get("genes") or []:
                conn.execute(
                    "INSERT INTO uniprot_entry_genes (accession, gene_symbol) VALUES (?, ?)",
                    (accession, str(gene).strip().upper()),
                )

    def status(self) -> dict[str, Any]:
        with self._connect() as conn:
            dataset = conn.execute(
                "SELECT * FROM localdb_datasets ORDER BY installed_at DESC LIMIT 1"
            ).fetchone()
            entry_count = conn.execute("SELECT COUNT(*) AS n FROM uniprot_entries").fetchone()["n"]
            gene_count = conn.execute("SELECT COUNT(*) AS n FROM uniprot_entry_genes").fetchone()["n"]
        return {
            "db_path": str(self.db_path),
            "offline": self.offline,
            "seed_path": str(self.seed_path),
            "dataset": dict(dataset) if dataset else None,
            "uniprot_records": int(entry_count or 0),
            "gene_symbols": int(gene_count or 0),
        }

    def fetch_uniprot(self, accession: str) -> dict[str, Any] | None:
        accession = str(accession or "").strip().upper()
        if not accession:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM uniprot_entries WHERE accession = ?",
                (accession,),
            ).fetchone()
            if row is None:
                return None
            genes = self._fetch_genes(conn, accession)
        return self._to_entry(row, genes=genes)

    def search_uniprot(self, query: str, max_results: int = 5) -> dict[str, Any]:
        query = str(query or "").strip()
        if not query:
            return {"query": "", "count": 0, "hits": []}

        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM uniprot_entries").fetchall()
            gene_map = self._fetch_gene_map(conn)

        ranked: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            score = self._score_entry(row, gene_map.get(row["accession"], []), query)
            if score > 0:
                ranked.append((score, self._to_search_hit(row, gene_map.get(row["accession"], []))))

        ranked.sort(key=lambda item: (-item[0], item[1]["accession"]))
        hits = [hit for _, hit in ranked[: max(max_results, 1)]]
        return {"query": query, "count": len(hits), "hits": hits}

    @staticmethod
    def _fetch_genes(conn: sqlite3.Connection, accession: str) -> list[str]:
        rows = conn.execute(
            "SELECT gene_symbol FROM uniprot_entry_genes WHERE accession = ? ORDER BY gene_symbol",
            (accession,),
        ).fetchall()
        return [str(row["gene_symbol"]) for row in rows]

    @staticmethod
    def _fetch_gene_map(conn: sqlite3.Connection) -> dict[str, list[str]]:
        rows = conn.execute(
            "SELECT accession, gene_symbol FROM uniprot_entry_genes ORDER BY accession, gene_symbol"
        ).fetchall()
        out: dict[str, list[str]] = {}
        for row in rows:
            out.setdefault(str(row["accession"]), []).append(str(row["gene_symbol"]))
        return out

    @staticmethod
    def _to_entry(row: sqlite3.Row, genes: Iterable[str]) -> dict[str, Any]:
        return {
            "accession": row["accession"],
            "id": row["entry_id"],
            "name": row["name"],
            "organism": row["organism"],
            "length": row["length"],
            "sequence": row["sequence"],
            "function": row["function"],
        }

    @staticmethod
    def _to_search_hit(row: sqlite3.Row, genes: Iterable[str]) -> dict[str, Any]:
        return {
            "accession": row["accession"],
            "id": row["entry_id"],
            "name": row["name"],
            "organism": row["organism"],
            "length": row["length"],
            "function": _truncate(row["function"]),
        }

    @staticmethod
    def _parse_gene_exact(query: str) -> str | None:
        match = _GENE_EXACT_RE.search(query or "")
        if not match:
            return None
        return (match.group(1) or match.group(2) or "").strip().upper() or None

    @staticmethod
    def _parse_organism(query: str) -> str | None:
        match = _ORGANISM_RE.search(query or "")
        if not match:
            return None
        return (match.group(1) or match.group(2) or "").strip() or None

    @staticmethod
    def _matched_accession(query: str) -> str | None:
        match = _ACCESSION_RE.search(query or "")
        return match.group(1).upper() if match else None

    def _score_entry(self, row: sqlite3.Row, genes: list[str], query: str) -> float:
        query_norm = _normalize_text(query)
        query_tokens = _tokens(query)
        accession = str(row["accession"]).upper()
        entry_id = str(row["entry_id"] or "").upper()
        name_norm = _normalize_text(str(row["name"] or ""))
        organism_norm = _normalize_text(str(row["organism"] or ""))
        function_norm = _normalize_text(str(row["function"] or ""))
        gene_set = {gene.upper() for gene in genes}

        accession_filter = self._matched_accession(query)
        gene_filter = self._parse_gene_exact(query)
        organism_filter = self._parse_organism(query)

        if organism_filter:
            filter_norm = _normalize_text(organism_filter)
            if filter_norm != organism_norm:
                return 0.0
        if gene_filter and gene_filter not in gene_set:
            return 0.0

        score = 0.0
        if accession_filter and accession_filter == accession:
            score += 1000.0
        if gene_filter and gene_filter in gene_set:
            score += 900.0
        if query_norm and query_norm in {accession.lower(), entry_id.lower(), name_norm}:
            score += 800.0
        if any(token.upper() in gene_set for token in query_tokens):
            score += 700.0
        if query_tokens and all(token in f"{name_norm} {' '.join(sorted(gene_set)).lower()}" for token in query_tokens):
            score += 500.0
        if query_tokens:
            score += sum(25.0 for token in query_tokens if token in name_norm)
            score += sum(6.0 for token in query_tokens if token in function_norm)
        if "human" in query.lower() or "homo sapiens" in query.lower():
            if organism_norm == "homo sapiens":
                score += 75.0
        if accession_filter and accession_filter in query.upper():
            score += 20.0
        if gene_filter and gene_filter in query.upper():
            score += 10.0
        return score


def get_local_biodb(
    db_path: str | os.PathLike[str] | None = None,
    seed_path: str | os.PathLike[str] | None = None,
    offline: bool | None = None,
) -> LocalBioDB:
    return LocalBioDB(db_path=db_path, seed_path=seed_path, offline=offline)
