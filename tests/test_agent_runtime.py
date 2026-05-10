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


class EchoBackend:
    name = "echo"
    model = "test/model"

    def chat(self, messages, **kwargs):
        user_text = messages[-1]["content"]
        return ChatResponse(content=f"echo: {user_text[:40]}")


class FallbackBackend:
    name = "fallback"
    model = "fallback/model"

    def chat(self, messages, **kwargs):
        system_text = messages[0]["content"]
        if "scientific tool route returned no usable" in system_text.lower():
            return ChatResponse(content="这是模型自身的兜底回答，未经过数据库验证。")
        return ChatResponse(content="tool-grounded summary")


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


def test_agent_model_only_answer_is_labeled_and_skips_tools():
    agent = Agent(DummyBackend(), trace_dir="./traces", session_dir="./sessions")
    out = agent.answer_model_only("你是谁")

    assert out["skill"] == "model_only"
    assert out["annotation"]["kind"] == "model_only"
    assert out["evidence"]["notes"] == ["No external tools or database evidence were used for this answer."]
    assert out["trace_steps"][0]["skill"] == "model_only"
    assert not any(event.get("kind") == "tool_call" for event in out["trace"])


def test_agent_model_only_prompt_identifies_biology_agent():
    agent = Agent(EchoBackend(), trace_dir="./traces", session_dir="./sessions")
    out = agent.answer_model_only("你是谁")
    system_prompt = next(event for event in out["trace"] if event["kind"] == "model_request")["messages"][0]["content"]

    assert "biology and life-science agent" in system_prompt
    assert "我是一个生物学/生命科学 Agent" in system_prompt
    assert "MODEL-ONLY" in system_prompt
    assert "Configured backend model id: test/model" in system_prompt


def test_agent_model_only_fallback_covers_common_intro_questions():
    assert "DNA 是细胞中主要的遗传信息载体" in Agent._model_only_fallback_summary("What is DNA?")
    assert "RNA 是参与遗传信息读取" in Agent._model_only_fallback_summary("什么是RNA")
    assert "PCR 是一种在体外扩增" in Agent._model_only_fallback_summary("介绍一下PCR")
    assert "转录是把 DNA" in Agent._model_only_fallback_summary("Explain transcription")
    assert "基因表达是遗传信息" in Agent._model_only_fallback_summary("What is gene expression?")
    assert "可追溯的生命科学问答和分析" in Agent._model_only_fallback_summary("你有什么功能")
    assert "fallback/model" in Agent._model_only_fallback_summary(
        "你的基座模型是啥",
        backend_name="fallback",
        model_id="fallback/model",
    )


def test_agent_protein_fallback_hides_routine_uniprot_notes():
    summary = Agent._evidence_fallback_summary(
        "What is BRCA1?",
        "uniprot_lookup",
        {
            "annotation": {
                "kind": "protein",
                "accession": "P38398",
                "name": "Breast cancer type 1 susceptibility protein",
                "organism": "Homo sapiens",
            },
            "confidence": 0.85,
            "notes": [
                "Used gene-specific search fallback for BRCA1",
                "Used search, top hit: P38398",
            ],
            "entry": {
                "accession": "P38398",
                "name": "Breast cancer type 1 susceptibility protein",
                "organism": "Homo sapiens",
                "length": 1863,
                "function": "E3 ubiquitin-protein ligase (PubMed:10500182, PubMed:12887909).",
            },
            "search": {"query": "gene_exact:BRCA1", "count": 5, "hits": []},
        },
    )

    assert "BRCA1 resolves to Breast cancer type 1 susceptibility protein" in summary
    assert "Used gene-specific search fallback" not in summary
    assert "Used search, top hit" not in summary
    assert "PubMed:10500182" not in summary


def test_agent_adds_model_only_fallback_when_tool_has_no_result(monkeypatch):
    import open_rosalind.orchestrator.agent as agent_module

    def fake_handler(payload, trace=None):
        return {
            "annotation": {"kind": "protein"},
            "confidence": 0.0,
            "notes": ["No results found"],
            "entry": {},
            "search": {"query": payload.get("query"), "count": 0, "hits": []},
        }

    monkeypatch.setitem(agent_module.SKILLS_V2, "uniprot_lookup", None)
    monkeypatch.setitem(agent_module.SKILL_REGISTRY, "uniprot_lookup", fake_handler)
    agent = Agent(FallbackBackend(), trace_dir="./traces", session_dir="./sessions")
    out = agent.analyze("What is NOT_A_REAL_PROTEIN?", mode="uniprot")

    assert out["model_only_fallback_applied"] is True
    assert "## Model-only fallback" in out["summary"]
    assert "未经过数据库验证" in out["summary"]
    assert any(event["kind"] == "model_only_fallback_request" for event in out["trace"])
