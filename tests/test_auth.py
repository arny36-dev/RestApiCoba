"""API-key authentication behaviour on the protected employee endpoints."""

from fastapi.testclient import TestClient

from tests.conftest import TEST_API_KEY

PROTECTED_GET = "/api/v1/employees"


def test_missing_api_key_returns_401(anon_client: TestClient) -> None:
    response = anon_client.get(PROTECTED_GET)
    assert response.status_code == 401
    assert "detail" in response.json()


def test_incorrect_api_key_returns_401(anon_client: TestClient) -> None:
    response = anon_client.get(PROTECTED_GET, headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401


def test_valid_api_key_is_accepted(anon_client: TestClient) -> None:
    response = anon_client.get(PROTECTED_GET, headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    assert "data" in response.json()


def test_protected_write_endpoints_require_key(anon_client: TestClient) -> None:
    assert anon_client.post(PROTECTED_GET, json={"surname": "X"}).status_code == 401
    assert anon_client.get("/api/v1/employee-types").status_code == 401


def test_health_endpoints_are_open(anon_client: TestClient) -> None:
    # Liveness and DB health must work without a key (used by Docker HEALTHCHECK).
    assert anon_client.get("/health").status_code == 200
    assert anon_client.get("/api/v1/db/health").status_code == 200
