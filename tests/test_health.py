from fastapi.testclient import TestClient

from app.main import create_app


def test_health_check_returns_standard_response() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert body["error"] is None
    assert "trace_id" in body["meta"]
    assert "timestamp" in body["meta"]
