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
