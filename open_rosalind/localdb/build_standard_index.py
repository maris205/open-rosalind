"""Build simple Standard-tier local KB indexes from downloaded source files.

This intentionally starts with two low-friction assets:
  - SQLite FTS5 for common text/name lookups.
  - Swiss-Prot FASTA plus optional BLAST database files.

The builder avoids service dependencies so the Standard package is usable
before MySQL/Elasticsearch are deployed.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import shutil
import sqlite3
import subprocess
import time
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path("/autodl-fs/data/open-rosalind-kb/standard")
DEFAULT_LIMITS = {
    "hgnc": 0,
    "ncbi_gene_human": 0,
    "ncbi_gene_scan": 250_000,
    "reactome_human": 0,
    "go_terms": 0,
    "clinvar_gene": 0,
    "clinvar_variants": 200_000,
    "clinvar_variant_scan": 300_000,
    "uniprot_fasta": 0,
    "pubmed": 2_000,
}


@dataclass(frozen=True, slots=True)
class StandardIndexConfig:
    root: Path
    index_dir: Path
    db_path: Path
    blast_dir: Path
    limits: dict[str, int]
    make_blast: bool


class StandardIndexBuilder:
    def __init__(self, config: StandardIndexConfig):
        self.config = config
        self.raw = config.root / "raw"

    def build(self) -> dict[str, Any]:
        self.config.index_dir.mkdir(parents=True, exist_ok=True)
        self.config.blast_dir.mkdir(parents=True, exist_ok=True)
        self._init_sqlite()
        counts = {
            "hgnc": self._index_hgnc(),
            "ncbi_gene_human": self._index_ncbi_gene_human(),
            "reactome_human": self._index_reactome_human(),
            "go_terms": self._index_go_terms(),
            "clinvar_gene": self._index_clinvar_gene_summary(),
            "clinvar_variants": self._index_clinvar_variants(),
            "pubmed": self._index_pubmed_baseline_sample(),
        }
        self._rebuild_fts()
        blast = self._build_blast_assets()
        self._write_manifest(counts, blast)
        return {"db_path": str(self.config.db_path), "counts": counts, "blast": blast}

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        exact = str(query or "").strip().upper()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT kind, source_id, name, symbol, organism, source, bm25(search_index) AS score
                FROM search_index
                WHERE search_index MATCH ?
                ORDER BY
                  CASE WHEN upper(coalesce(symbol, '')) = ? THEN 0 ELSE 1 END,
                  score
                LIMIT ?
                """,
                (fts_query(query), exact, max(limit, 1)),
            ).fetchall()
        return [dict(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.config.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self) -> None:
        for path in (
            self.config.db_path,
            Path(f"{self.config.db_path}-wal"),
            Path(f"{self.config.db_path}-shm"),
        ):
            if path.exists():
                path.unlink()
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode = OFF;
                PRAGMA synchronous = OFF;
                PRAGMA temp_store = MEMORY;

                CREATE TABLE documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    symbol TEXT,
                    name TEXT,
                    organism TEXT,
                    description TEXT,
                    source TEXT NOT NULL,
                    source_url TEXT,
                    payload_json TEXT
                );

                CREATE VIRTUAL TABLE search_index USING fts5(
                    kind,
                    source_id,
                    symbol,
                    name,
                    organism,
                    description,
                    source,
                    content='documents',
                    content_rowid='id',
                    tokenize='unicode61'
                );

                CREATE INDEX idx_documents_kind_symbol ON documents(kind, symbol);
                CREATE INDEX idx_documents_source_id ON documents(source_id);
                CREATE INDEX idx_documents_organism ON documents(organism);
                """
            )

    def _insert_documents(self, records: Iterable[dict[str, Any]]) -> int:
        count = 0
        with self._connect() as conn:
            batch = []
            for record in records:
                batch.append(
                    (
                        clean(record.get("kind")),
                        clean(record.get("source_id")),
                        clean(record.get("symbol")),
                        clean(record.get("name")),
                        clean(record.get("organism")),
                        clean(record.get("description")),
                        clean(record.get("source")),
                        clean(record.get("source_url")),
                        json.dumps(record.get("payload") or {}, ensure_ascii=False, separators=(",", ":")),
                    )
                )
                count += 1
                if len(batch) >= 5_000:
                    conn.executemany(
                        """
                        INSERT INTO documents
                        (kind, source_id, symbol, name, organism, description, source, source_url, payload_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        batch,
                    )
                    batch.clear()
            if batch:
                conn.executemany(
                    """
                    INSERT INTO documents
                    (kind, source_id, symbol, name, organism, description, source, source_url, payload_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    batch,
                )
        return count

    def _rebuild_fts(self) -> None:
        with self._connect() as conn:
            conn.execute("INSERT INTO search_index(search_index) VALUES ('rebuild')")

    def _index_hgnc(self) -> int:
        path = self.raw / "hgnc" / "hgnc_complete_set.txt"
        if not path.exists():
            return 0
        def records() -> Iterator[dict[str, Any]]:
            for row in limited(tsv_rows(path), self.config.limits["hgnc"]):
                symbol = row.get("symbol")
                if not symbol:
                    continue
                yield {
                    "kind": "hgnc_gene",
                    "source_id": row.get("hgnc_id") or symbol,
                    "symbol": symbol,
                    "name": row.get("name"),
                    "organism": "Homo sapiens",
                    "description": join_text(
                        row.get("name"),
                        row.get("alias_symbol"),
                        row.get("alias_name"),
                        row.get("prev_symbol"),
                        row.get("prev_name"),
                        row.get("gene_group"),
                        row.get("uniprot_ids"),
                        row.get("omim_id"),
                    ),
                    "source": "HGNC",
                    "source_url": "https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt",
                    "payload": pick(row, "entrez_id", "ensembl_gene_id", "uniprot_ids", "location", "alias_symbol"),
                }
        return self._insert_documents(records())

    def _index_ncbi_gene_human(self) -> int:
        path = self.raw / "ncbi_gene" / "gene_info.gz"
        if not path.exists():
            return 0
        if self.config.limits["ncbi_gene_human"] <= 0:
            return 0

        def records() -> Iterator[dict[str, Any]]:
            for row in limited_matches(
                tsv_rows_gzip(path),
                item_limit=self.config.limits["ncbi_gene_human"],
                scan_limit=self.config.limits["ncbi_gene_scan"],
                predicate=lambda item: item.get("#tax_id") == "9606",
            ):
                if row.get("#tax_id") != "9606":
                    continue
                gene_id = row.get("GeneID")
                symbol = row.get("Symbol")
                if not gene_id or not symbol:
                    continue
                yield {
                    "kind": "ncbi_gene",
                    "source_id": gene_id,
                    "symbol": symbol,
                    "name": dash_to_empty(row.get("Full_name_from_nomenclature_authority")) or row.get("description"),
                    "organism": "Homo sapiens",
                    "description": join_text(
                        row.get("description"),
                        row.get("Synonyms"),
                        row.get("Other_designations"),
                        row.get("dbXrefs"),
                        row.get("map_location"),
                    ),
                    "source": "NCBI Gene",
                    "source_url": f"https://www.ncbi.nlm.nih.gov/gene/{gene_id}",
                    "payload": pick(row, "chromosome", "map_location", "type_of_gene", "Modification_date"),
                }
        return self._insert_documents(records())

    def _index_reactome_human(self) -> int:
        path = self.raw / "reactome" / "ReactomePathways.txt"
        if not path.exists():
            return 0

        def records() -> Iterator[dict[str, Any]]:
            with path.open("rt", encoding="utf-8", errors="replace") as handle:
                reader = csv.reader(handle, delimiter="\t")
                for row in limited_matches(
                    reader,
                    item_limit=self.config.limits["reactome_human"],
                    predicate=lambda item: len(item) >= 3 and item[2] == "Homo sapiens",
                ):
                    if len(row) < 3 or row[2] != "Homo sapiens":
                        continue
                    yield {
                        "kind": "reactome_pathway",
                        "source_id": row[0],
                        "symbol": None,
                        "name": row[1],
                        "organism": row[2],
                        "description": row[1],
                        "source": "Reactome",
                        "source_url": f"https://reactome.org/content/detail/{row[0]}",
                        "payload": {},
                    }
        return self._insert_documents(records())

    def _index_go_terms(self) -> int:
        path = self.raw / "go" / "go-basic.obo"
        if not path.exists():
            return 0
        return self._insert_documents(limited(parse_go_obo(path), self.config.limits["go_terms"]))

    def _index_clinvar_gene_summary(self) -> int:
        path = self.raw / "clinvar" / "gene_specific_summary.txt"
        if not path.exists():
            return 0

        def records() -> Iterator[dict[str, Any]]:
            for row in limited(tsv_rows_from_header(path, "#Symbol"), self.config.limits["clinvar_gene"]):
                symbol = row.get("#Symbol")
                gene_id = row.get("GeneID")
                if not symbol or not gene_id:
                    continue
                yield {
                    "kind": "clinvar_gene_summary",
                    "source_id": gene_id,
                    "symbol": symbol,
                    "name": symbol,
                    "organism": "Homo sapiens",
                    "description": join_text(
                        "ClinVar gene summary",
                        row.get("Alleles_reported_Pathogenic_Likely_pathogenic"),
                        row.get("Number_uncertain"),
                        row.get("Number_with_conflicts"),
                        row.get("Gene_MIM_number"),
                    ),
                    "source": "ClinVar",
                    "source_url": "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/gene_specific_summary.txt",
                    "payload": row,
                }
        return self._insert_documents(records())

    def _index_clinvar_variants(self) -> int:
        path = self.raw / "clinvar" / "variant_summary.txt.gz"
        if not path.exists():
            return 0
        if self.config.limits["clinvar_variants"] <= 0:
            return 0

        def records() -> Iterator[dict[str, Any]]:
            for row in limited_matches(
                tsv_rows_gzip(path),
                item_limit=self.config.limits["clinvar_variants"],
                scan_limit=self.config.limits["clinvar_variant_scan"],
                predicate=lambda item: bool(item.get("VariationID") and item.get("GeneSymbol") and item.get("Name")),
            ):
                variation_id = row.get("VariationID")
                gene = row.get("GeneSymbol")
                name = row.get("Name")
                if not variation_id or not gene or not name:
                    continue
                yield {
                    "kind": "clinvar_variant",
                    "source_id": variation_id,
                    "symbol": gene,
                    "name": name,
                    "organism": "Homo sapiens",
                    "description": join_text(
                        row.get("ClinicalSignificance"),
                        row.get("PhenotypeList"),
                        row.get("RS# (dbSNP)"),
                        row.get("RCVaccession"),
                    ),
                    "source": "ClinVar",
                    "source_url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{variation_id}/",
                    "payload": pick(
                        row,
                        "AlleleID",
                        "Type",
                        "GeneID",
                        "HGNC_ID",
                        "ClinicalSignificance",
                        "PhenotypeList",
                        "Assembly",
                        "Chromosome",
                        "Start",
                        "Stop",
                    ),
                }
        return self._insert_documents(records())

    def _index_pubmed_baseline_sample(self) -> int:
        baseline = self.raw / "pubmed" / "baseline"
        if not baseline.exists():
            return 0
        limit = self.config.limits["pubmed"]
        if limit <= 0:
            return 0

        def records() -> Iterator[dict[str, Any]]:
            count = 0
            for xml_path in sorted(baseline.glob("pubmed*.xml.gz")):
                for record in parse_pubmed_xml(xml_path):
                    yield record
                    count += 1
                    if count >= limit:
                        return
        return self._insert_documents(records())

    def _build_blast_assets(self) -> dict[str, Any]:
        source = self.raw / "uniprot" / "uniprot_sprot.fasta.gz"
        fasta = self.config.blast_dir / "swissprot.fasta"
        result: dict[str, Any] = {"source": str(source), "fasta": str(fasta), "makeblastdb": False}
        if not source.exists():
            result["status"] = "missing_source"
            return result
        if not fasta.exists() or fasta.stat().st_size == 0:
            with gzip.open(source, "rt", encoding="utf-8", errors="replace") as src, fasta.open("wt", encoding="utf-8") as dst:
                shutil.copyfileobj(src, dst)
        result["fasta_size_bytes"] = fasta.stat().st_size
        makeblastdb = shutil.which("makeblastdb")
        if not self.config.make_blast:
            result["status"] = "fasta_ready"
            result["reason"] = "makeblastdb disabled"
            return result
        if not makeblastdb:
            result["status"] = "fasta_ready"
            result["reason"] = "makeblastdb not found"
            return result
        cmd = [
            makeblastdb,
            "-in",
            str(fasta),
            "-dbtype",
            "prot",
            "-parse_seqids",
            "-out",
            str(self.config.blast_dir / "swissprot"),
        ]
        completed = subprocess.run(cmd, check=False, text=True, capture_output=True)
        result["makeblastdb"] = True
        result["returncode"] = completed.returncode
        result["stdout"] = completed.stdout[-1000:]
        result["stderr"] = completed.stderr[-1000:]
        result["status"] = "blastdb_ready" if completed.returncode == 0 else "makeblastdb_failed"
        return result

    def _write_manifest(self, counts: dict[str, int], blast: dict[str, Any]) -> None:
        manifest = {
            "dataset": "open_rosalind_kb_standard_index",
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "root": str(self.config.root),
            "db_path": str(self.config.db_path),
            "counts": counts,
            "blast": blast,
        }
        (self.config.index_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def parse_go_obo(path: Path) -> Iterator[dict[str, Any]]:
    current: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line == "[Term]":
            if current.get("id") and current.get("name"):
                yield go_record(current)
            current = {}
            continue
        if not line or line.startswith("!"):
            continue
        key, _, value = line.partition(": ")
        if key in {"id", "name", "namespace", "def"} and value and key not in current:
            current[key] = value
    if current.get("id") and current.get("name"):
        yield go_record(current)


def go_record(term: dict[str, str]) -> dict[str, Any]:
    go_id = term["id"]
    name = term["name"]
    namespace = term.get("namespace")
    definition = term.get("def", "")
    return {
        "kind": "go_term",
        "source_id": go_id,
        "symbol": None,
        "name": name,
        "organism": None,
        "description": join_text(namespace, definition),
        "source": "Gene Ontology",
        "source_url": f"https://amigo.geneontology.org/amigo/term/{go_id}",
        "payload": term,
    }


def parse_pubmed_xml(path: Path) -> Iterator[dict[str, Any]]:
    import xml.etree.ElementTree as ET

    with gzip.open(path, "rb") as handle:
        context = ET.iterparse(handle, events=("end",))
        for _, elem in context:
            if elem.tag != "PubmedArticle":
                continue
            pmid = text_at(elem, ".//PMID")
            title = text_at(elem, ".//ArticleTitle")
            journal = text_at(elem, ".//Journal/Title") or text_at(elem, ".//ISOAbbreviation")
            year = text_at(elem, ".//PubDate/Year")
            abstract = " ".join(" ".join(node.itertext()).strip() for node in elem.findall(".//AbstractText"))
            if pmid and title:
                yield {
                    "kind": "pubmed_article",
                    "source_id": pmid,
                    "symbol": None,
                    "name": title,
                    "organism": None,
                    "description": join_text(journal, year, abstract),
                    "source": "PubMed",
                    "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "payload": {"pmid": pmid, "journal": journal, "year": year},
                }
            elem.clear()


def text_at(elem: Any, path: str) -> str:
    node = elem.find(path)
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def tsv_rows(path: Path) -> Iterator[dict[str, str]]:
    with path.open("rt", encoding="utf-8", errors="replace", newline="") as handle:
        yield from csv.DictReader(handle, delimiter="\t")


def tsv_rows_from_header(path: Path, header_prefix: str) -> Iterator[dict[str, str]]:
    with path.open("rt", encoding="utf-8", errors="replace", newline="") as handle:
        for line in handle:
            if line.startswith(header_prefix):
                yield from csv.DictReader([line, *handle], delimiter="\t")
                return


def tsv_rows_gzip(path: Path) -> Iterator[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as handle:
        yield from csv.DictReader(handle, delimiter="\t")


def limited(rows: Iterable[Any], limit: int) -> Iterator[Any]:
    for idx, row in enumerate(rows):
        if limit and idx >= limit:
            break
        yield row


def limited_matches(
    rows: Iterable[Any],
    *,
    item_limit: int,
    scan_limit: int = 0,
    predicate: Any | None = None,
) -> Iterator[Any]:
    count = 0
    for idx, row in enumerate(rows):
        if scan_limit and idx >= scan_limit:
            break
        if predicate is not None and not predicate(row):
            continue
        yield row
        count += 1
        if item_limit and count >= item_limit:
            break


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text and text != "-" else None


def dash_to_empty(value: Any) -> str | None:
    return clean(value)


def join_text(*values: Any) -> str:
    return " ".join(str(value).strip() for value in values if clean(value))


def pick(row: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {key: row.get(key) for key in keys if clean(row.get(key))}


def fts_query(query: str) -> str:
    tokens = [token.replace('"', "") for token in str(query or "").split() if token.strip()]
    if not tokens:
        return '""'
    return " OR ".join(f'"{token}"' for token in tokens)


def parse_limits(raw_limits: list[str] | None) -> dict[str, int]:
    limits = dict(DEFAULT_LIMITS)
    for item in raw_limits or []:
        key, _, value = item.partition("=")
        if key not in limits or not value:
            raise ValueError(f"Unknown or invalid limit {item!r}")
        limits[key] = max(int(value), 0)
    return limits


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build simple Open-Rosalind Standard KB indexes")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Standard KB root directory")
    parser.add_argument("--index-dir", default=None, help="Index output directory")
    parser.add_argument("--db-path", default=None, help="SQLite FTS database path")
    parser.add_argument("--blast-dir", default=None, help="BLAST asset output directory")
    parser.add_argument("--limit", action="append", help="Override source row limit, e.g. clinvar_variants=50000")
    parser.add_argument("--skip-blastdb", action="store_true", help="Prepare FASTA but do not run makeblastdb")
    parser.add_argument("--smoke-query", action="append", help="Run a search query after building")
    return parser.parse_args(argv)


def build_config(args: argparse.Namespace) -> StandardIndexConfig:
    root = Path(args.root)
    index_dir = Path(args.index_dir) if args.index_dir else root / "index"
    return StandardIndexConfig(
        root=root,
        index_dir=index_dir,
        db_path=Path(args.db_path) if args.db_path else index_dir / "open_rosalind_standard.sqlite",
        blast_dir=Path(args.blast_dir) if args.blast_dir else index_dir / "blast",
        limits=parse_limits(args.limit),
        make_blast=not args.skip_blastdb,
    )


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    builder = StandardIndexBuilder(build_config(args))
    result = builder.build()
    if args.smoke_query:
        result["smoke"] = {query: builder.search(query, limit=5) for query in args.smoke_query}
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
