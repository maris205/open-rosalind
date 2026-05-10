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
DEFAULT_SEED_PATH = Path(__file__).resolve().parent / "seeds" / "bio_minimal.json"
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


def _json_load(value: Any, default: Any) -> Any:
    if value in {None, ""}:
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return default


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _normalize_species_name(species: str) -> str:
    clean = " ".join(str(species or "").replace("_", " ").split())
    if not clean:
        return "Homo sapiens"
    parts = clean.split(" ")
    if len(parts) == 1:
        return parts[0]
    return " ".join([parts[0].capitalize(), *[part.lower() for part in parts[1:]]])


def _normalize_species_key(species: str) -> str:
    return " ".join(str(species or "").replace("_", " ").split()).lower()


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

        CREATE TABLE IF NOT EXISTS pubmed_articles (
            pmid TEXT PRIMARY KEY,
            title TEXT,
            authors_json TEXT,
            journal TEXT,
            year TEXT,
            doi TEXT,
            abstract TEXT,
            source TEXT,
            source_url TEXT
        );

        CREATE TABLE IF NOT EXISTS pubmed_article_terms (
            pmid TEXT NOT NULL,
            term TEXT NOT NULL,
            FOREIGN KEY (pmid) REFERENCES pubmed_articles(pmid) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_pubmed_article_terms_term
            ON pubmed_article_terms(term);
        CREATE INDEX IF NOT EXISTS idx_pubmed_articles_year
            ON pubmed_articles(year);

        CREATE TABLE IF NOT EXISTS ncbi_gene_entries (
            gene_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            name TEXT,
            description TEXT,
            summary TEXT,
            species TEXT,
            chromosome TEXT,
            map_location TEXT,
            aliases_json TEXT,
            other_designations_json TEXT,
            nomenclature_name TEXT,
            nomenclature_status TEXT,
            mim_ids_json TEXT,
            genomic_location_json TEXT,
            source TEXT,
            source_url TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_ncbi_gene_entries_symbol
            ON ncbi_gene_entries(symbol);
        CREATE INDEX IF NOT EXISTS idx_ncbi_gene_entries_species
            ON ncbi_gene_entries(species);

        CREATE TABLE IF NOT EXISTS ensembl_gene_entries (
            ensembl_gene_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            species TEXT NOT NULL,
            description TEXT,
            biotype TEXT,
            object_type TEXT,
            assembly_name TEXT,
            seq_region_name TEXT,
            start INTEGER,
            end INTEGER,
            strand INTEGER,
            canonical_transcript TEXT,
            transcripts_json TEXT,
            source TEXT,
            source_url TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_ensembl_gene_entries_symbol_species
            ON ensembl_gene_entries(symbol, species);

        CREATE TABLE IF NOT EXISTS ensembl_xrefs (
            ensembl_gene_id TEXT NOT NULL,
            dbname TEXT,
            primary_id TEXT,
            display_id TEXT,
            description TEXT,
            synonyms_json TEXT,
            info_type TEXT,
            db_display_name TEXT,
            linkage_types_json TEXT,
            FOREIGN KEY (ensembl_gene_id) REFERENCES ensembl_gene_entries(ensembl_gene_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_ensembl_xrefs_ensembl_gene_id
            ON ensembl_xrefs(ensembl_gene_id);
        CREATE INDEX IF NOT EXISTS idx_ensembl_xrefs_dbname
            ON ensembl_xrefs(dbname);
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
            conn.execute("DELETE FROM ensembl_xrefs")
            conn.execute("DELETE FROM ensembl_gene_entries")
            conn.execute("DELETE FROM ncbi_gene_entries")
            conn.execute("DELETE FROM pubmed_article_terms")
            conn.execute("DELETE FROM pubmed_articles")
            conn.execute("DELETE FROM uniprot_entry_genes")
            conn.execute("DELETE FROM uniprot_entries")
            conn.execute(
                "INSERT OR REPLACE INTO localdb_metadata (key, value) VALUES (?, ?)",
                ("seed_state", "missing"),
            )
            return

        seed = json.loads(self.seed_path.read_text(encoding="utf-8"))
        records = list(seed.get("records") or seed.get("uniprot") or [])
        pubmed_records = list(seed.get("pubmed") or [])
        ncbi_gene_records = list(seed.get("ncbi_gene") or [])
        ensembl_records = list(seed.get("ensembl_gene") or [])
        dataset_name = str(seed.get("dataset") or "bio_minimal")
        dataset_version = str(seed.get("version") or "0")
        source = str(seed.get("source") or "UniProtKB reviewed seed")
        source_url = str(seed.get("source_url") or "https://rest.uniprot.org")
        record_count = len(records) + len(pubmed_records) + len(ncbi_gene_records) + len(ensembl_records)

        conn.execute("DELETE FROM localdb_datasets")
        conn.execute("DELETE FROM localdb_metadata")
        conn.execute("DELETE FROM ensembl_xrefs")
        conn.execute("DELETE FROM ensembl_gene_entries")
        conn.execute("DELETE FROM ncbi_gene_entries")
        conn.execute("DELETE FROM pubmed_article_terms")
        conn.execute("DELETE FROM pubmed_articles")
        conn.execute("DELETE FROM uniprot_entry_genes")
        conn.execute("DELETE FROM uniprot_entries")

        conn.execute(
            """
            INSERT OR REPLACE INTO localdb_datasets
            (dataset_name, dataset_version, source, source_url, installed_at, record_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (dataset_name, dataset_version, source, source_url, time.time(), record_count),
        )
        metadata = {
            "seed_dataset": dataset_name,
            "seed_version": dataset_version,
            "seed_source": source,
            "seed_source_url": source_url,
            "seed_records": str(record_count),
            "seed_uniprot_records": str(len(records)),
            "seed_pubmed_records": str(len(pubmed_records)),
            "seed_ncbi_gene_records": str(len(ncbi_gene_records)),
            "seed_ensembl_gene_records": str(len(ensembl_records)),
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

        for record in pubmed_records:
            pmid = str(record["pmid"]).strip()
            conn.execute(
                """
                INSERT OR REPLACE INTO pubmed_articles
                (pmid, title, authors_json, journal, year, doi, abstract, source, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pmid,
                    record.get("title"),
                    _json_dump(record.get("authors") or []),
                    record.get("journal"),
                    str(record.get("year") or "") or None,
                    record.get("doi"),
                    record.get("abstract"),
                    record.get("source"),
                    record.get("source_url"),
                ),
            )
            terms = list(record.get("terms") or [])
            terms.extend(_tokens(" ".join([str(record.get("title") or ""), str(record.get("abstract") or "")])))
            seen_terms: set[str] = set()
            for term in terms:
                normalized = str(term).strip().lower()
                if not normalized or normalized in seen_terms:
                    continue
                seen_terms.add(normalized)
                conn.execute(
                    "INSERT INTO pubmed_article_terms (pmid, term) VALUES (?, ?)",
                    (pmid, normalized),
                )

        for record in ncbi_gene_records:
            gene_id = str(record["gene_id"]).strip()
            conn.execute(
                """
                INSERT OR REPLACE INTO ncbi_gene_entries
                (gene_id, symbol, name, description, summary, species, chromosome, map_location,
                 aliases_json, other_designations_json, nomenclature_name, nomenclature_status,
                 mim_ids_json, genomic_location_json, source, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    gene_id,
                    str(record.get("symbol") or "").strip().upper(),
                    record.get("name"),
                    record.get("description"),
                    record.get("summary"),
                    record.get("species"),
                    record.get("chromosome"),
                    record.get("map_location"),
                    _json_dump(record.get("aliases") or []),
                    _json_dump(record.get("other_designations") or []),
                    record.get("nomenclature_name"),
                    record.get("nomenclature_status"),
                    _json_dump(record.get("mim_ids") or []),
                    _json_dump(record.get("genomic_location") or {}),
                    record.get("source"),
                    record.get("source_url"),
                ),
            )

        for record in ensembl_records:
            ensembl_gene_id = str(record["ensembl_gene_id"]).strip()
            conn.execute(
                """
                INSERT OR REPLACE INTO ensembl_gene_entries
                (ensembl_gene_id, symbol, species, description, biotype, object_type, assembly_name,
                 seq_region_name, start, end, strand, canonical_transcript, transcripts_json, source, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ensembl_gene_id,
                    str(record.get("symbol") or "").strip().upper(),
                    str(record.get("species") or "homo_sapiens"),
                    record.get("description"),
                    record.get("biotype"),
                    record.get("object_type"),
                    record.get("assembly_name"),
                    record.get("seq_region_name"),
                    record.get("start"),
                    record.get("end"),
                    record.get("strand"),
                    record.get("canonical_transcript"),
                    _json_dump(record.get("transcripts") or []),
                    record.get("source"),
                    record.get("source_url"),
                ),
            )
            for xref in record.get("xrefs") or []:
                conn.execute(
                    """
                    INSERT INTO ensembl_xrefs
                    (ensembl_gene_id, dbname, primary_id, display_id, description, synonyms_json,
                     info_type, db_display_name, linkage_types_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ensembl_gene_id,
                        xref.get("dbname"),
                        xref.get("primary_id"),
                        xref.get("display_id"),
                        xref.get("description"),
                        _json_dump(xref.get("synonyms") or []),
                        xref.get("info_type"),
                        xref.get("db_display_name"),
                        _json_dump(xref.get("linkage_types") or []),
                    ),
                )

    def status(self) -> dict[str, Any]:
        with self._connect() as conn:
            dataset = conn.execute(
                "SELECT * FROM localdb_datasets ORDER BY installed_at DESC LIMIT 1"
            ).fetchone()
            entry_count = conn.execute("SELECT COUNT(*) AS n FROM uniprot_entries").fetchone()["n"]
            gene_count = conn.execute("SELECT COUNT(*) AS n FROM uniprot_entry_genes").fetchone()["n"]
            pubmed_count = conn.execute("SELECT COUNT(*) AS n FROM pubmed_articles").fetchone()["n"]
            ncbi_gene_count = conn.execute("SELECT COUNT(*) AS n FROM ncbi_gene_entries").fetchone()["n"]
            ensembl_gene_count = conn.execute("SELECT COUNT(*) AS n FROM ensembl_gene_entries").fetchone()["n"]
            ensembl_xref_count = conn.execute("SELECT COUNT(*) AS n FROM ensembl_xrefs").fetchone()["n"]
        return {
            "db_path": str(self.db_path),
            "offline": self.offline,
            "seed_path": str(self.seed_path),
            "dataset": dict(dataset) if dataset else None,
            "uniprot_records": int(entry_count or 0),
            "gene_symbols": int(gene_count or 0),
            "pubmed_records": int(pubmed_count or 0),
            "ncbi_gene_records": int(ncbi_gene_count or 0),
            "ensembl_gene_records": int(ensembl_gene_count or 0),
            "ensembl_xref_records": int(ensembl_xref_count or 0),
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

    def search_pubmed(self, query: str, max_results: int = 5) -> dict[str, Any]:
        query = str(query or "").strip()
        if not query:
            return {"query": "", "count": 0, "hits": []}

        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM pubmed_articles").fetchall()
            term_map = self._fetch_pubmed_term_map(conn)

        ranked: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            score = self._score_pubmed(row, term_map.get(str(row["pmid"]), []), query)
            if score > 0:
                ranked.append((score, self._to_pubmed_hit(row)))
        ranked.sort(key=lambda item: (-item[0], item[1].get("year") or "", item[1]["pmid"]))
        hits = [hit for _, hit in ranked[: max(max_results, 1)]]
        return {"query": query, "count": len(hits), "hits": hits}

    def fetch_pubmed_metadata(self, pmids: list[str] | str) -> dict[str, Any]:
        pmid_list = self._normalize_pmids(pmids)
        if not pmid_list:
            return {"count": 0, "records": []}

        records: list[dict[str, Any]] = []
        with self._connect() as conn:
            for pmid in pmid_list:
                row = conn.execute("SELECT * FROM pubmed_articles WHERE pmid = ?", (pmid,)).fetchone()
                if row is not None:
                    records.append(self._to_pubmed_metadata(row))
        return {"count": len(records), "records": records}

    def fetch_pubmed_abstract(self, pmids: list[str] | str) -> dict[str, Any]:
        pmid_list = self._normalize_pmids(pmids)
        if not pmid_list:
            return {"count": 0, "records": []}

        records: list[dict[str, Any]] = []
        with self._connect() as conn:
            for pmid in pmid_list:
                row = conn.execute("SELECT * FROM pubmed_articles WHERE pmid = ?", (pmid,)).fetchone()
                if row is not None:
                    records.append(
                        {
                            "pmid": str(row["pmid"]),
                            "title": row["title"] or "",
                            "abstract": row["abstract"] or "",
                        }
                    )
        return {"count": len(records), "records": records}

    def search_ncbi_gene(self, query: str, species: str = "Homo sapiens", max_results: int = 3) -> dict[str, Any]:
        clean_query = str(query or "").strip()
        if not clean_query:
            return {"query": "", "species": _normalize_species_name(species), "count": 0, "ids": [], "query_translation": None}

        clean_species = _normalize_species_name(species)
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM ncbi_gene_entries").fetchall()

        ranked: list[tuple[float, str]] = []
        for row in rows:
            score = self._score_ncbi_gene(row, clean_query, clean_species)
            if score > 0:
                ranked.append((score, str(row["gene_id"])))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        ids = [gene_id for _, gene_id in ranked[: max(max_results, 1)]]
        return {
            "query": clean_query,
            "species": clean_species,
            "count": len(ids),
            "ids": ids,
            "query_translation": f"{clean_query}[gene] AND {clean_species}[organism]" if ids else None,
        }

    def fetch_ncbi_gene(self, gene_id: str) -> dict[str, Any] | None:
        clean_id = str(gene_id or "").strip()
        if not clean_id:
            return None
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM ncbi_gene_entries WHERE gene_id = ?", (clean_id,)).fetchone()
        if row is None:
            return None
        return self._to_ncbi_gene(row)

    def lookup_ensembl_gene(self, symbol: str, species: str = "homo_sapiens") -> dict[str, Any] | None:
        clean_symbol = str(symbol or "").strip().upper()
        clean_species = str(species or "homo_sapiens").strip() or "homo_sapiens"
        if not clean_symbol:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM ensembl_gene_entries WHERE symbol = ? AND lower(replace(species, '_', ' ')) = ?",
                (clean_symbol, _normalize_species_key(clean_species)),
            ).fetchone()
            if row is None:
                return None
        return self._to_ensembl_gene(row, query=clean_symbol)

    def fetch_ensembl_xrefs(self, ensembl_id: str, external_db: str | None = None) -> dict[str, Any] | None:
        clean_id = str(ensembl_id or "").strip()
        if not clean_id:
            return None
        with self._connect() as conn:
            exists = conn.execute(
                "SELECT 1 FROM ensembl_gene_entries WHERE ensembl_gene_id = ?",
                (clean_id,),
            ).fetchone()
            if exists is None:
                return None
            if external_db and external_db.strip():
                rows = conn.execute(
                    "SELECT * FROM ensembl_xrefs WHERE ensembl_gene_id = ? AND dbname = ?",
                    (clean_id, external_db.strip()),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM ensembl_xrefs WHERE ensembl_gene_id = ?",
                    (clean_id,),
                ).fetchall()
        records = [self._to_ensembl_xref(row) for row in rows]
        return {"ensembl_id": clean_id, "count": len(records), "records": records}

    @staticmethod
    def _fetch_genes(conn: sqlite3.Connection, accession: str) -> list[str]:
        rows = conn.execute(
            "SELECT gene_symbol FROM uniprot_entry_genes WHERE accession = ? ORDER BY gene_symbol",
            (accession,),
        ).fetchall()
        return [str(row["gene_symbol"]) for row in rows]

    @staticmethod
    def _normalize_pmids(pmids: list[str] | str) -> list[str]:
        if isinstance(pmids, str):
            raw_values = [pmids]
        else:
            raw_values = list(pmids or [])
        out: list[str] = []
        for raw in raw_values:
            pmid = str(raw).strip()
            if pmid and pmid not in out:
                out.append(pmid)
        return out

    @staticmethod
    def _fetch_pubmed_term_map(conn: sqlite3.Connection) -> dict[str, list[str]]:
        rows = conn.execute("SELECT pmid, term FROM pubmed_article_terms ORDER BY pmid, term").fetchall()
        out: dict[str, list[str]] = {}
        for row in rows:
            out.setdefault(str(row["pmid"]), []).append(str(row["term"]))
        return out

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
    def _to_pubmed_hit(row: sqlite3.Row) -> dict[str, Any]:
        pmid = str(row["pmid"])
        return {
            "pmid": pmid,
            "title": row["title"],
            "authors": _json_load(row["authors_json"], []),
            "journal": row["journal"],
            "year": row["year"],
            "url": row["source_url"] or f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        }

    @staticmethod
    def _to_pubmed_metadata(row: sqlite3.Row) -> dict[str, Any]:
        pmid = str(row["pmid"])
        return {
            "pmid": pmid,
            "title": row["title"],
            "authors": _json_load(row["authors_json"], []),
            "journal": row["journal"],
            "year": row["year"],
            "doi": row["doi"],
            "url": row["source_url"] or f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        }

    @staticmethod
    def _to_ncbi_gene(row: sqlite3.Row) -> dict[str, Any]:
        gene_id = str(row["gene_id"])
        return {
            "gene_id": gene_id,
            "found": True,
            "symbol": row["symbol"],
            "name": row["name"],
            "description": row["description"],
            "summary": row["summary"],
            "species": row["species"],
            "chromosome": row["chromosome"],
            "map_location": row["map_location"],
            "aliases": _json_load(row["aliases_json"], []),
            "other_designations": _json_load(row["other_designations_json"], []),
            "nomenclature_name": row["nomenclature_name"],
            "nomenclature_status": row["nomenclature_status"],
            "mim_ids": _json_load(row["mim_ids_json"], []),
            "genomic_location": _json_load(row["genomic_location_json"], {}),
            "url": row["source_url"] or f"https://www.ncbi.nlm.nih.gov/gene/{gene_id}",
        }

    @staticmethod
    def _to_ensembl_gene(row: sqlite3.Row, query: str) -> dict[str, Any]:
        ensembl_gene_id = str(row["ensembl_gene_id"])
        transcripts = _json_load(row["transcripts_json"], [])
        return {
            "query": query,
            "species": row["species"],
            "found": True,
            "ensembl_gene_id": ensembl_gene_id,
            "symbol": row["symbol"],
            "description": row["description"],
            "biotype": row["biotype"],
            "object_type": row["object_type"],
            "assembly_name": row["assembly_name"],
            "seq_region_name": row["seq_region_name"],
            "start": row["start"],
            "end": row["end"],
            "strand": row["strand"],
            "canonical_transcript": row["canonical_transcript"],
            "n_transcripts": len(transcripts),
            "transcripts": transcripts[:20],
            "url": row["source_url"] or f"https://www.ensembl.org/id/{ensembl_gene_id}",
        }

    @staticmethod
    def _to_ensembl_xref(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "dbname": row["dbname"],
            "primary_id": row["primary_id"],
            "display_id": row["display_id"],
            "description": row["description"],
            "synonyms": _json_load(row["synonyms_json"], []),
            "info_type": row["info_type"],
            "db_display_name": row["db_display_name"],
            "linkage_types": _json_load(row["linkage_types_json"], []),
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

    @staticmethod
    def _score_pubmed(row: sqlite3.Row, terms: list[str], query: str) -> float:
        query_tokens = _tokens(query)
        if not query_tokens:
            return 0.0
        title_norm = _normalize_text(str(row["title"] or ""))
        abstract_norm = _normalize_text(str(row["abstract"] or ""))
        term_set = {term.lower() for term in terms}
        score = 0.0
        for token in query_tokens:
            token_norm = token.lower()
            if token_norm in term_set:
                score += 50.0
            if token_norm in title_norm:
                score += 30.0
            if token_norm in abstract_norm:
                score += 8.0
        if all(token.lower() in f"{title_norm} {abstract_norm} {' '.join(term_set)}" for token in query_tokens):
            score += 100.0
        return score

    @staticmethod
    def _score_ncbi_gene(row: sqlite3.Row, query: str, species: str) -> float:
        query_norm = _normalize_text(query)
        query_upper = query.strip().upper()
        species_key = _normalize_species_key(species)
        row_species = _normalize_species_key(str(row["species"] or ""))
        if species_key and row_species and species_key != row_species:
            return 0.0

        symbol = str(row["symbol"] or "").upper()
        aliases = [str(alias).upper() for alias in _json_load(row["aliases_json"], [])]
        haystack = _normalize_text(
            " ".join(
                [
                    str(row["symbol"] or ""),
                    str(row["name"] or ""),
                    str(row["description"] or ""),
                    str(row["summary"] or ""),
                    " ".join(aliases),
                ]
            )
        )

        score = 0.0
        if query.strip() == str(row["gene_id"]):
            score += 1000.0
        if query_upper == symbol:
            score += 900.0
        if query_upper in aliases:
            score += 600.0
        if query_norm and query_norm in haystack:
            score += 100.0
        for token in _tokens(query):
            if token in haystack:
                score += 20.0
        return score


def get_local_biodb(
    db_path: str | os.PathLike[str] | None = None,
    seed_path: str | os.PathLike[str] | None = None,
    offline: bool | None = None,
) -> LocalBioDB:
    return LocalBioDB(db_path=db_path, seed_path=seed_path, offline=offline)
