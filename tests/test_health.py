from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_db_health_returns_connected(client: TestClient) -> None:
    response = client.get("/api/v1/db/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}
