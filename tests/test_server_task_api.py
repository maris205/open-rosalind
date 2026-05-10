from fastapi.testclient import TestClient

from open_rosalind.server import app


client = TestClient(app)


def test_task_run_exposes_expected_and_executed_workflow():
    response = client.post(
        "/api/task/run",
        json={
            "goal": "Assess TP53 p.R175H mutation impact and supporting literature",
            "max_steps": 3,
        },
    )
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "completed"
    assert len(body["steps"]) == 1
    step = body["steps"][0]
    assert step["expected_workflow"] == "workflow_mutation_assessment"
    assert step["executed_workflow"] == "mutation_assessment"
    assert isinstance(step["summary"], str)
    assert isinstance(step["evidence"], dict)
    assert isinstance(step["trace"], list)
    assert "error" in step


def test_chat_model_only_response_is_labeled(monkeypatch):
    def fake_answer_model_only(question, session_id=None, conversation_history=None):
        return {
            "session_id": session_id or "model-only-test",
            "skill": "model_only",
            "summary": "**我是一个生物学/生命科学 Agent。**",
            "annotation": {"kind": "model_only", "source": "language_model"},
            "confidence": 0.5,
            "notes": ["No external tools or database evidence were used for this answer."],
            "evidence": {
                "annotation": {"kind": "model_only", "source": "language_model"},
                "notes": ["No external tools or database evidence were used for this answer."],
            },
            "trace_path": "traces/model-only-test.jsonl",
            "trace": [{"kind": "model_response", "route": "model_only"}],
            "trace_steps": [
                {
                    "skill": "model_only",
                    "input": {"question": question},
                    "output": {"source": "language_model"},
                    "status": "success",
                    "latency_ms": None,
                }
            ],
        }

    monkeypatch.setattr("open_rosalind.server.agent.answer_model_only", fake_answer_model_only)

    response = client.post("/api/chat", json={"message": "你是谁"})
    assert response.status_code == 200
    body = response.json()

    assert body["execution_mode"] == "model_only"
    assert body["skill"] == "model_only"
    assert body["annotation"]["kind"] == "model_only"
    assert body["evidence"]["annotation"]["kind"] == "model_only"
    assert body["trace_steps"][0]["skill"] == "model_only"


def test_chat_single_step_exposes_model_only_fallback_flag(monkeypatch):
    def fake_run(text, session_id=None, mode=None, follow_up_session=None, conversation_history=None):
        return {
            "session_id": session_id or "single-step-test",
            "skill": "uniprot_lookup",
            "summary": "Tool summary\n\n## Model-only fallback\nFallback text",
            "annotation": {"kind": "protein"},
            "confidence": 0.0,
            "notes": ["Tool route returned low-confidence or no-result evidence; added a model-only fallback."],
            "evidence": {"annotation": {"kind": "protein"}, "confidence": 0.0},
            "trace_steps": [],
            "model_only_fallback_applied": True,
        }

    monkeypatch.setattr("open_rosalind.server.select_mode", lambda message: ("single_step", "test route"))
    monkeypatch.setattr("open_rosalind.server.runner.run", fake_run)

    response = client.post("/api/chat", json={"message": "What is NOT_A_REAL_PROTEIN?"})
    assert response.status_code == 200
    body = response.json()

    assert body["execution_mode"] == "single_step"
    assert body["model_only_fallback_applied"] is True
    assert "## Model-only fallback" in body["summary"]
