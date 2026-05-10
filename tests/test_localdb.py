from __future__ import annotations

import pytest

from open_rosalind.localdb import LocalBioDB
from open_rosalind.tools import ensembl as ensembl_tools
from open_rosalind.tools import ncbi_gene as ncbi_gene_tools
from open_rosalind.tools import pubmed as pubmed_tools
from open_rosalind.tools import uniprot as uniprot_tools


def test_localdb_seeds_minimal_uniprot_records(tmp_path):
    db = LocalBioDB(db_path=tmp_path / "local.db")
    status = db.status()
    assert status["uniprot_records"] == 5
    assert status["pubmed_records"] == 5
    assert status["ncbi_gene_records"] == 6
    assert status["ensembl_gene_records"] == 6
    assert status["dataset"]["dataset_name"] == "bio_minimal"
    assert status["dataset"]["dataset_version"] == "2026-05-10.seed.v3"

    record = db.fetch_uniprot("P38398")
    assert record is not None
    assert record["accession"] == "P38398"
    assert record["name"].startswith("Breast cancer type 1 susceptibility protein")
    assert record["sequence"].startswith("MDLSALRV")


def test_localdb_search_supports_gene_exact_and_organism_filter(tmp_path):
    db = LocalBioDB(db_path=tmp_path / "local.db")
    out = db.search_uniprot('gene_exact:TP53 AND organism_name:"Homo sapiens"', max_results=5)
    assert out["count"] == 1
    assert out["hits"][0]["accession"] == "P04637"


def test_localdb_search_supports_high_frequency_demo_queries(tmp_path):
    db = LocalBioDB(db_path=tmp_path / "local.db")
    insulin = db.search_uniprot("insulin", max_results=5)
    beta = db.search_uniprot("hemoglobin beta", max_results=5)
    alpha = db.search_uniprot("HBA1", max_results=5)
    assert insulin["hits"][0]["accession"] == "P01308"
    assert beta["hits"][0]["accession"] == "P68871"
    assert alpha["hits"][0]["accession"] == "P69905"


def test_localdb_supports_pubmed_gene_and_ensembl(tmp_path):
    db = LocalBioDB(db_path=tmp_path / "local.db")

    pubmed = db.search_pubmed("BRCA1 DNA repair", max_results=3)
    assert pubmed["hits"][0]["pmid"] == "25956865"

    metadata = db.fetch_pubmed_metadata(["25956865"])
    assert metadata["records"][0]["title"].startswith("BRCA1")

    abstracts = db.fetch_pubmed_abstract(["25956865"])
    assert "BRCA1" in abstracts["records"][0]["abstract"]

    gene = db.fetch_ncbi_gene("7157")
    assert gene["symbol"] == "TP53"

    gene_search = db.search_ncbi_gene("TP53", species="Homo sapiens", max_results=3)
    assert gene_search["ids"][0] == "7157"

    ensembl = db.lookup_ensembl_gene("TP53", species="homo_sapiens")
    assert ensembl["ensembl_gene_id"] == "ENSG00000141510"

    xrefs = db.fetch_ensembl_xrefs("ENSG00000141510")
    assert any(record["primary_id"] == "7157" for record in xrefs["records"])


def test_uniprot_tools_use_localdb_before_remote(monkeypatch, tmp_path):
    monkeypatch.setenv("OPEN_ROSALIND_LOCALDB_PATH", str(tmp_path / "local.db"))
    monkeypatch.setenv("OPEN_ROSALIND_OFFLINE", "1")

    monkeypatch.setattr(uniprot_tools, "_remote_search", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("remote search should not run")))
    monkeypatch.setattr(uniprot_tools, "_remote_fetch", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("remote fetch should not run")))

    search = uniprot_tools.search("BRCA1", size=5)
    assert search["count"] == 1
    assert search["hits"][0]["accession"] == "P38398"

    record = uniprot_tools.fetch("P04637")
    assert record["accession"] == "P04637"
    assert record["id"] == "P53_HUMAN"


def test_pubmed_and_gene_tools_use_localdb_before_remote(monkeypatch, tmp_path):
    monkeypatch.setenv("OPEN_ROSALIND_LOCALDB_PATH", str(tmp_path / "local.db"))
    monkeypatch.setenv("OPEN_ROSALIND_OFFLINE", "1")

    monkeypatch.setattr(pubmed_tools, "_remote_search", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("remote pubmed search should not run")))
    monkeypatch.setattr(pubmed_tools, "_remote_fetch_metadata", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("remote pubmed metadata should not run")))
    monkeypatch.setattr(pubmed_tools, "_remote_fetch_abstract", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("remote pubmed abstract should not run")))
    monkeypatch.setattr(ncbi_gene_tools, "_remote_search_gene", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("remote ncbi gene search should not run")))
    monkeypatch.setattr(ncbi_gene_tools, "_remote_fetch_gene", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("remote ncbi gene fetch should not run")))
    monkeypatch.setattr(ensembl_tools, "_remote_lookup_gene", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("remote ensembl lookup should not run")))
    monkeypatch.setattr(ensembl_tools, "_remote_fetch_xrefs", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("remote ensembl xrefs should not run")))

    pubmed = pubmed_tools.search("BRCA1 DNA repair", max_results=3)
    assert pubmed["hits"][0]["pmid"] == "25956865"

    metadata = pubmed_tools.fetch_metadata(["25956865"])
    assert metadata["records"][0]["pmid"] == "25956865"

    abstract = pubmed_tools.fetch_abstract(["25956865"])
    assert "BRCA1" in abstract["records"][0]["abstract"]

    gene_search = ncbi_gene_tools.search_gene("TP53", species="Homo sapiens", max_results=3)
    assert gene_search["ids"][0] == "7157"

    gene = ncbi_gene_tools.fetch_gene("7157")
    assert gene["symbol"] == "TP53"

    ensembl = ensembl_tools.lookup_gene("TP53", species="homo_sapiens")
    assert ensembl["ensembl_gene_id"] == "ENSG00000141510"

    xrefs = ensembl_tools.fetch_xrefs("ENSG00000141510")
    assert any(record["primary_id"] == "7157" for record in xrefs["records"])


def test_uniprot_tools_offline_missing_accession_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("OPEN_ROSALIND_LOCALDB_PATH", str(tmp_path / "local.db"))
    monkeypatch.setenv("OPEN_ROSALIND_OFFLINE", "1")
    with pytest.raises(LookupError):
        uniprot_tools.fetch("Q9DOESNOTEXIST")


def test_uniprot_tools_fallback_to_remote_when_local_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("OPEN_ROSALIND_LOCALDB_PATH", str(tmp_path / "local.db"))
    monkeypatch.delenv("OPEN_ROSALIND_OFFLINE", raising=False)

    monkeypatch.setattr(
        uniprot_tools,
        "_remote_search",
        lambda query, size=5, fields=None: {
            "query": query,
            "count": 1,
            "hits": [
                {
                    "accession": "QREMOTE1",
                    "id": "REMOTE_HUMAN",
                    "name": "Remote protein",
                    "organism": "Homo sapiens",
                    "length": 123,
                    "function": "Remote function",
                }
            ],
        },
    )
    monkeypatch.setattr(
        uniprot_tools,
        "_remote_fetch",
        lambda accession: {
            "accession": accession,
            "id": "REMOTE_HUMAN",
            "name": "Remote protein",
            "organism": "Homo sapiens",
            "length": 123,
            "sequence": "MREMOTE",
            "function": "Remote function",
        },
    )

    search = uniprot_tools.search("QREMOTE1", size=5)
    assert search["hits"][0]["accession"] == "QREMOTE1"

    record = uniprot_tools.fetch("QREMOTE1")
    assert record["id"] == "REMOTE_HUMAN"
