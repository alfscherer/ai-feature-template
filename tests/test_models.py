from fastapi.testclient import TestClient


def test_list_models_returns_at_least_one_default(client: TestClient) -> None:
    response = client.get("/api/models")

    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert sum(1 for m in body if m["is_default"]) == 1
