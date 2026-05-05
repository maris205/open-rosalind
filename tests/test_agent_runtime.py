from open_rosalind.backends.base import ChatResponse
from open_rosalind.orchestrator.agent import Agent


class DummyBackend:
    name = "dummy"

    def chat(self, messages, **kwargs):
        return ChatResponse(content="dummy summary")


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
