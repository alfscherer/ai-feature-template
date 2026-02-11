from fastapi.testclient import TestClient


def test_analyze_rejects_empty_feedback(client: TestClient) -> None:
    response = client.post("/api/analyze", json={"feedback": ""})

    assert response.status_code == 422


def test_analyze_rejects_oversized_feedback(client: TestClient) -> None:
    response = client.post("/api/analyze", json={"feedback": "x" * 5000})

    assert response.status_code == 422


def test_analyze_not_yet_wired_to_a_provider(client: TestClient) -> None:
    response = client.post("/api/analyze", json={"feedback": "The export button is broken."})

    assert response.status_code == 501
