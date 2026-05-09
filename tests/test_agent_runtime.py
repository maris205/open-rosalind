from open_rosalind.backends.base import ChatResponse
from open_rosalind.orchestrator.agent import Agent


class DummyBackend:
    name = "dummy"

    def chat(self, messages, **kwargs):
        return ChatResponse(content="dummy summary")


class FailingBackend:
    name = "failing"

    def chat(self, messages, **kwargs):
        raise RuntimeError("Internal Server Error")


def test_agent_prefers_skills_v2_runtime():
    agent = Agent(DummyBackend(), trace_dir="./traces", session_dir="./sessions")
    out = agent.analyze("ATGGCCAAATTAA", mode="sequence")
    assert out["skill"] == "sequence_basic_analysis"
    assert out["annotation"]["primary_type"] == "dna"
    assert out["summary"] == "dummy summary"


def test_agent_workflow_override_avoids_trace_self_reference():
    agent = Agent(DummyBackend(), trace_dir="./traces", session_dir="./sessions")
    out = agent.analyze(
        "Assess TP53 p.R175H mutation impact and supporting literature",
        mode="mutation",
        workflow="workflow_mutation_assessment",
    )
    assert out["skill"] == "workflow_mutation_assessment"
    assert out["annotation"]["workflow"] == "mutation_assessment"
    assert out["summary"] == "dummy summary"


def test_agent_strips_embedded_evidence_section_from_summary():
    class EvidenceBackend:
        name = "dummy"

        def chat(self, messages, **kwargs):
            return ChatResponse(
                content=(
                    "BRCA1 is a DNA repair protein [UniProt:P38398].\n\n"
                    "### Details\n"
                    "* Human protein [UniProt:P38398]\n\n"
                    "### Evidence\n"
                    "* [UniProt:P38398]"
                )
            )

    agent = Agent(EvidenceBackend(), trace_dir="./traces", session_dir="./sessions")
    out = agent.analyze("What is BRCA1?", mode="uniprot")
    assert "### Evidence" not in out["summary"]
    assert out["summary"].endswith("* Human protein [UniProt:P38398]")


def test_agent_workflow_payload_override_replaces_routed_payload():
    agent = Agent(DummyBackend(), trace_dir="./traces", session_dir="./sessions")
    out = agent.analyze(
        "Analyze the provided protein sequence through the constrained protein annotation workflow.",
        mode="sequence",
        workflow="workflow_protein_annotation",
        payload_override={"sequence": "MVKVGVNGFGRIGRLVTRA"},
    )
    assert out["skill"] == "workflow_protein_annotation"
    assert out["annotation"]["workflow"] == "protein_annotation"


def test_agent_backend_error_uses_evidence_fallback_summary(monkeypatch):
    from open_rosalind.tools import ncbi_blast as ncbi_blast_tools

    def fake_run_search(**kwargs):
        return {
            "program": "blastp",
            "database": "swissprot",
            "rid": "RID123",
            "status": "READY",
            "has_hits": True,
            "query_summaries": [
                {
                    "query_title": "query",
                    "hit_count_returned": 1,
                    "hit_count_available": 1,
                    "truncated": False,
                    "top_hits": [
                        {
                            "rank": 1,
                            "accession": "P04797",
                            "title": "Glyceraldehyde-3-phosphate dehydrogenase",
                            "evalue": 1.65e-05,
                            "bit_score": 42.0,
                        }
                    ],
                }
            ],
        }

    monkeypatch.setattr(ncbi_blast_tools, "run_search", fake_run_search)
    agent = Agent(FailingBackend(), trace_dir="./traces", session_dir="./sessions")
    out = agent.analyze(
        "Analyze sequence MVKVGVNGFGRIGRLVTRA and find similar proteins",
        workflow="ncbi_blast_search",
        payload_override={
            "program": "blastp",
            "database": "swissprot",
            "query_fasta": ">query\nMVKVGVNGFGRIGRLVTRA\n",
        },
    )

    assert "Model backend unavailable" not in out["summary"]
    assert "NCBI BLAST found similar proteins" in out["summary"]
    assert "P04797" in out["summary"]
    assert any(event["kind"] == "model_error" for event in out["trace"])


def test_agent_evidence_fallback_summary_for_no_hit_protein():
    summary = Agent._evidence_fallback_summary(
        "What is NOT_A_REAL_PROTEIN?",
        "uniprot_lookup",
        {
            "annotation": {"kind": "protein"},
            "confidence": 0.0,
            "notes": ["No results found"],
            "entry": {},
            "search": {"query": "NOT_A_REAL_PROTEIN", "count": 0, "hits": []},
        },
    )

    assert "Model backend unavailable" not in summary
    assert "UniProt did not return" in summary
    assert "No results found" in summary
