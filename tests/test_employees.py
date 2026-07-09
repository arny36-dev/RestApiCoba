import sqlite3
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


def _create(client: TestClient, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"surname": "Smith", **overrides}
    response = client.post("/api/v1/employees", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_sets_active_and_bozp_defaults(client: TestClient) -> None:
    record = _create(client, surname="DefaultsCheck", forename="John")
    assert record["active"] == 1
    assert record["bozp_state"] == "NO BOZP"
    assert record["bozp_required"] == 0
    assert record["object_id"] == 127  # DEFAULT_OBJECT_ID from test env
    assert record["created"] is not None
    assert record["modified"] is not None


def test_create_requires_surname(client: TestClient) -> None:
    response = client.post("/api/v1/employees", json={"forename": "NoSurname"})
    assert response.status_code == 422


def test_unknown_fields_are_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/employees", json={"surname": "X", "no_such_field": "boom"})
    assert response.status_code == 422

    record = _create(client, surname="PatchGuard")
    response = client.patch(f"/api/v1/employees/{record['id']}", json={"unknown_column": 1})
    assert response.status_code == 422


def test_id_and_active_cannot_be_written(client: TestClient) -> None:
    assert client.post("/api/v1/employees", json={"surname": "X", "id": 999}).status_code == 422
    assert client.post("/api/v1/employees", json={"surname": "X", "active": 0}).status_code == 422

    record = _create(client, surname="Immutable")
    assert client.patch(f"/api/v1/employees/{record['id']}", json={"id": 5}).status_code == 422
    assert client.patch(f"/api/v1/employees/{record['id']}", json={"active": 0}).status_code == 422


def test_rfid_gate_validated_on_create(client: TestClient) -> None:
    assert (
        client.post("/api/v1/employees", json={"surname": "X", "rfid_gate": 2}).status_code == 422
    )
    record = _create(client, surname="GateOk", rfid_gate=1, rfid_littlegate=0)
    assert record["rfid_gate"] == 1
    assert record["rfid_littlegate"] == 0


def test_list_filters_and_sorting(client: TestClient) -> None:
    _create(client, surname="Zebra", forename="Anna", rfid_gate=1)
    _create(client, surname="zebrak", forename="Bob", rfid_gate=0)

    response = client.get("/api/v1/employees", params={"surname": "zebra"})
    assert response.status_code == 200
    body = response.json()
    surnames = [row["surname"] for row in body["data"]]
    assert surnames == sorted(surnames, key=str.lower)  # surname ASC
    assert len(surnames) == 2

    # rfid_gate=2 means "all", 1 filters
    all_rows = client.get("/api/v1/employees", params={"surname": "zebra", "rfid_gate": 2})
    assert len(all_rows.json()["data"]) == 2
    gated = client.get("/api/v1/employees", params={"surname": "zebra", "rfid_gate": 1})
    assert [r["surname"] for r in gated.json()["data"]] == ["Zebra"]

    assert body["pagination"]["page"] == 1


def test_list_always_filters_active(client: TestClient, db_path: Path) -> None:
    record = _create(client, surname="SoonInactive")
    connection = sqlite3.connect(db_path)
    connection.execute("UPDATE er_reg_employees SET active = 0 WHERE id = ?", (record["id"],))
    connection.commit()
    connection.close()

    response = client.get("/api/v1/employees", params={"surname": "SoonInactive"})
    assert response.json()["data"] == []
    assert client.get(f"/api/v1/employees/{record['id']}").status_code == 404


def test_page_size_above_max_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/employees", params={"page_size": 999})
    assert response.status_code == 422
    # MAX_PAGE_SIZE is 50 in the test environment (see conftest.py).
    assert "50" in response.json()["detail"]


def test_get_missing_employee_returns_404(client: TestClient) -> None:
    assert client.get("/api/v1/employees/999999").status_code == 404


def test_put_and_patch_update_fields(client: TestClient) -> None:
    record = _create(client, surname="Before", forename="Old")
    employee_id = record["id"]

    response = client.put(f"/api/v1/employees/{employee_id}", json={"surname": "AfterPut"})
    assert response.status_code == 200
    assert response.json()["surname"] == "AfterPut"

    response = client.patch(f"/api/v1/employees/{employee_id}", json={"note": "patched"})
    assert response.status_code == 200
    body = response.json()
    assert body["note"] == "patched"
    assert body["surname"] == "AfterPut"


def test_delete_is_soft_and_sets_active_zero(client: TestClient, db_path: Path) -> None:
    record = _create(client, surname="ToDelete")
    employee_id = record["id"]

    response = client.delete(f"/api/v1/employees/{employee_id}")
    assert response.status_code == 200
    assert response.json() == {"status": "deleted", "id": employee_id}

    # Row still physically exists with active = 0.
    connection = sqlite3.connect(db_path)
    row = connection.execute(
        "SELECT active FROM er_reg_employees WHERE id = ?", (employee_id,)
    ).fetchone()
    connection.close()
    assert row is not None
    assert row[0] == 0

    assert client.get(f"/api/v1/employees/{employee_id}").status_code == 404
    assert client.delete(f"/api/v1/employees/{employee_id}").status_code == 404


def test_employee_types_read_only_listing(client: TestClient) -> None:
    response = client.get("/api/v1/employee-types")
    assert response.status_code == 200
    names = [row["name"] for row in response.json()["data"]]
    # Only active types for DEFAULT_OBJECT_ID=127, sorted by name.
    assert names == ["employee", "visitor"]

    # No write methods exist for employee types.
    assert client.post("/api/v1/employee-types", json={"name": "x"}).status_code == 405
    assert client.delete("/api/v1/employee-types").status_code == 405


def test_generic_table_routes_are_gone(client: TestClient) -> None:
    assert client.get("/api/v1/tables").status_code == 404
    assert client.get("/api/v1/er_reg_employees").status_code == 404
    assert client.get("/api/v1/er_reg_employees/metadata").status_code == 404
    assert client.get("/api/v1/srv_sendmails").status_code == 404
