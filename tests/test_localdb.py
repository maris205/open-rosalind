from __future__ import annotations

import pytest

from open_rosalind.localdb import LocalBioDB
from open_rosalind.tools import uniprot as uniprot_tools


def test_localdb_seeds_minimal_uniprot_records(tmp_path):
    db = LocalBioDB(db_path=tmp_path / "local.db")
    status = db.status()
    assert status["uniprot_records"] == 5
    assert status["dataset"]["dataset_name"] == "uniprot_minimal"
    assert status["dataset"]["dataset_version"] == "2026-05-10.seed.v2"

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
