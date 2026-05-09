"""Test harness basic functionality."""
from open_rosalind.backends.base import ChatResponse
from open_rosalind.backends import build_backend
from open_rosalind.config import load_config
from open_rosalind.harness import AgentAdapter, Task, TaskRunner
from open_rosalind.harness.planner import ConstrainedPlanner
from open_rosalind.orchestrator import Agent


def test_harness_protein_research():
    """Test protein research task (workflow annotation → literature)."""
    cfg = load_config()
    backend = build_backend(cfg["backend"])
    agent = Agent(backend)
    adapter = AgentAdapter(agent)
    runner = TaskRunner(adapter)

    task = Task(
        task_id="test_001",
        user_goal="Analyze this protein sequence and find related papers: MVKVGVNGFGRIGRLVTRA",
        max_steps=3,
    )

    result = runner.run(task)

    assert result.status == "completed"
    assert len(result.steps) <= 2
    assert result.final_report is not None
    assert len(result.state.evidence_pool) > 0
    assert result.steps[0].expected_workflow == "workflow_protein_annotation"
    print(f"✅ Task {result.task_id} completed with {len(result.steps)} steps")
    print(f"   Known entities: {result.state.known_entities}")
    print(f"   Evidence records: {len(result.state.evidence_pool)}")


def test_harness_literature_review():
    """Test literature review task."""
    cfg = load_config()
    backend = build_backend(cfg["backend"])
    agent = Agent(backend)
    adapter = AgentAdapter(agent)
    runner = TaskRunner(adapter)

    task = Task(
        task_id="test_002",
        user_goal="Find papers about CRISPR base editing",
        max_steps=2,
    )

    result = runner.run(task)

    assert result.status == "completed"
    assert len(result.steps) >= 1
    assert result.final_report is not None
    print(f"✅ Task {result.task_id} completed with {len(result.steps)} steps")


def test_harness_mutation_assessment():
    """Test mutation assessment task."""
    cfg = load_config()
    backend = build_backend(cfg["backend"])
    agent = Agent(backend)
    adapter = AgentAdapter(agent)
    runner = TaskRunner(adapter)

    task = Task(
        task_id="test_003",
        user_goal="Assess this mutation: WT: MEEPQ MT: p.R175H",
        max_steps=3,
    )

    result = runner.run(task)

    assert result.status == "completed"
    assert len(result.steps) <= 3
    assert result.final_report is not None
    print(f"✅ Task {result.task_id} completed with {len(result.steps)} steps")


class DummyBackend:
    name = "dummy"

    def chat(self, messages, **kwargs):
        return ChatResponse(content="dummy summary")


def test_harness_uses_expected_workflow_override():
    agent = Agent(DummyBackend(), trace_dir="./traces", session_dir="./sessions")
    adapter = AgentAdapter(agent)
    runner = TaskRunner(adapter)

    task = Task(
        task_id="test_004",
        user_goal="Assess TP53 p.R175H mutation impact and supporting literature",
        max_steps=3,
    )

    result = runner.run(task)

    assert result.status == "completed"
    assert len(result.steps) == 1
    step = result.steps[0]
    assert step.expected_workflow == "workflow_mutation_assessment"
    assert step.status == "success"
    assert step.agent_result is not None
    assert step.agent_result["extracted_entities"]["workflow"] == "mutation_assessment"
    assert result.state.known_entities["workflow"] == "mutation_assessment"
    assert result.to_dict()["steps"][0]["executed_workflow"] == "mutation_assessment"


def test_harness_protein_research_uses_workflow_override():
    agent = Agent(DummyBackend(), trace_dir="./traces", session_dir="./sessions")
    adapter = AgentAdapter(agent)
    runner = TaskRunner(adapter)

    task = Task(
        task_id="test_005",
        user_goal="Analyze this protein sequence and find related papers: MVKVGVNGFGRIGRLVTRA",
        max_steps=3,
    )

    result = runner.run(task)

    assert result.status == "completed"
    assert len(result.steps) == 2
    first_step = result.steps[0]
    assert first_step.expected_workflow == "workflow_protein_annotation"
    assert first_step.status == "success"
    assert first_step.agent_result is not None
    assert first_step.agent_result["extracted_entities"]["workflow"] == "protein_annotation"
    assert result.state.known_entities["workflow"] == "protein_annotation"
    assert result.to_dict()["steps"][0]["executed_workflow"] == "protein_annotation"


def test_harness_planner_extracts_sequence_payload_for_homology_request():
    planner = ConstrainedPlanner()
    steps = planner.create_plan("Analyze sequence MVKVGVNGFGRIGRLVTRA and find similar proteins", max_steps=5)

    assert len(steps) == 2
    assert steps[0].expected_workflow == "workflow_protein_annotation"
    assert steps[0].payload_hint["sequence"] == "MVKVGVNGFGRIGRLVTRA"
    assert steps[1].expected_workflow == "ncbi_blast_search"
    assert steps[1].payload_hint["sequence"] == "MVKVGVNGFGRIGRLVTRA"


def test_harness_adapter_builds_blast_payload_for_homology_request():
    class CaptureAgent:
        def __init__(self):
            self.calls = []

        def analyze(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "summary": "dummy summary",
                "evidence": {"annotation": {"kind": "ncbi_blast"}},
                "trace_steps": [],
                "confidence": 0.8,
                "annotation": {"workflow": "ncbi_blast_search"},
            }

    agent = CaptureAgent()
    adapter = AgentAdapter(agent)

    result = adapter.run_step(
        "Search for similar proteins using NCBI BLAST and the grounded sequence query.",
        {},
        "ncbi_blast_search",
        {"sequence": "MVKVGVNGFGRIGRLVTRA"},
    )

    assert result.status == "success"
    assert agent.calls[0]["workflow"] == "ncbi_blast_search"
    payload = agent.calls[0]["payload_override"]
    assert payload["program"] == "blastp"
    assert payload["database"] == "swissprot"
    assert payload["query_fasta"] == ">query\nMVKVGVNGFGRIGRLVTRA\n"
    assert payload["max_queries"] == 1


def test_harness_planner_extracts_mutation_payload():
    planner = ConstrainedPlanner()
    steps = planner.create_plan("Assess TP53 p.R175H mutation impact and supporting literature", max_steps=3)

    assert len(steps) == 1
    assert steps[0].expected_workflow == "workflow_mutation_assessment"
    assert steps[0].payload_hint["gene_symbol"] == "TP53"
    assert steps[0].payload_hint["mutation"] == "p.R175H"


def test_harness_final_report_uses_lead_summary_only():
    class StubExecutor:
        def run_step(self, instruction, context, expected_workflow, payload_hint=None):
            return type("Result", (), {
                "status": "success",
                "summary": (
                    "**No protein match was found for the provided sequence.**\n\n"
                    "| Field | Value |\n| :--- | :--- |\n| Hit Count | 0 |\n\n"
                    "## Key findings\n- No UniProt match was found."
                ),
                "evidence": {},
                "trace": [],
                "confidence": 0.7,
                "extracted_entities": {"workflow": "protein_annotation"},
                "error": None,
                "to_dict": lambda self=None: {
                    "summary": (
                        "**No protein match was found for the provided sequence.**\n\n"
                        "| Field | Value |\n| :--- | :--- |\n| Hit Count | 0 |\n\n"
                        "## Key findings\n- No UniProt match was found."
                    ),
                    "evidence": {},
                    "trace": [],
                    "confidence": 0.7,
                    "extracted_entities": {"workflow": "protein_annotation"},
                    "status": "success",
                    "error": None,
                },
            })()

    runner = TaskRunner(StubExecutor())
    task = Task(
        task_id="test_006",
        user_goal="Analyze sequence MVKVGVNGFGRIGRLVTRA and find similar proteins",
        max_steps=2,
    )

    result = runner.run(task)

    assert "| Field | Value |" not in (result.final_report or "")
    assert "## Key findings" not in (result.final_report or "")
    assert "No protein match was found for the provided sequence." in (result.final_report or "")


def test_harness_lead_summary_preserves_tool_citation_identifiers():
    summary = TaskRunner._lead_summary(
        "**NCBI BLAST found similar proteins for the submitted sequence [tool:ncbi_blast.run_search].**"
    )

    assert summary == "NCBI BLAST found similar proteins for the submitted sequence [tool:ncbi_blast.run_search]."


if __name__ == "__main__":
    test_harness_protein_research()
    test_harness_literature_review()
    test_harness_mutation_assessment()
    test_harness_uses_expected_workflow_override()
    test_harness_protein_research_uses_workflow_override()
    print("\n✅ All harness tests passed")
