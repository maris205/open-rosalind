"""Test harness basic functionality."""
from open_rosalind.backends import build_backend
from open_rosalind.config import load_config
from open_rosalind.harness import AgentAdapter, Task, TaskRunner
from open_rosalind.orchestrator import Agent


def test_harness_protein_research():
    """Test protein research task (sequence → annotation → literature)."""
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
    assert len(result.steps) <= 3
    assert result.final_report is not None
    assert len(result.state.evidence_pool) > 0
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


if __name__ == "__main__":
    test_harness_protein_research()
    test_harness_literature_review()
    test_harness_mutation_assessment()
    print("\n✅ All harness tests passed")
