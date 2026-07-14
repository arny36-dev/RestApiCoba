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


def test_object_id_cannot_be_set_by_client(client: TestClient) -> None:
    # object_id sa vždy dopĺňa na DEFAULT_OBJECT_ID; klient ho nesmie posielať.
    assert (
        client.post("/api/v1/employees", json={"surname": "X", "object_id": 5}).status_code == 422
    )
    record = _create(client, surname="ObjectIdDefault")
    assert record["object_id"] == 127


def test_id_and_active_cannot_be_written(client: TestClient) -> None:
    assert client.post("/api/v1/employees", json={"surname": "X", "id": 999}).status_code == 422
    assert client.post("/api/v1/employees", json={"surname": "X", "active": 0}).status_code == 422

    record = _create(client, surname="Immutable")
    assert client.patch(f"/api/v1/employees/{record['id']}", json={"id": 5}).status_code == 422
    assert client.patch(f"/api/v1/employees/{record['id']}", json={"active": 0}).status_code == 422


def test_type_must_exist_in_employee_types(client: TestClient) -> None:
    # 'employee' je aktívny typ pre objekt 127 (viď conftest) -> prejde.
    record = _create(client, surname="ValidType", type="employee")
    assert record["type"] == "employee"

    # Neznámy typ -> 422.
    r = client.post("/api/v1/employees", json={"surname": "X", "type": "neexistuje"})
    assert r.status_code == 422
    assert "employee-types" in r.json()["detail"]

    # Neaktívny typ a typ iného objektu sú tiež neplatné.
    assert (
        client.post("/api/v1/employees", json={"surname": "X", "type": "inactive type"}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/employees", json={"surname": "X", "type": "other object type"}
        ).status_code
        == 422
    )


def test_type_validated_on_update(client: TestClient) -> None:
    record = _create(client, surname="UpdType")
    employee_id = record["id"]

    ok = client.patch(f"/api/v1/employees/{employee_id}", json={"type": "visitor"})
    assert ok.status_code == 200
    assert ok.json()["type"] == "visitor"

    bad = client.patch(f"/api/v1/employees/{employee_id}", json={"type": "neexistuje"})
    assert bad.status_code == 422


def test_rfid_gate_validated_on_create(client: TestClient) -> None:
    assert (
        client.post("/api/v1/employees", json={"surname": "X", "rfid_gate": 2}).status_code == 422
    )
    record = _create(client, surname="GateOk", rfid_gate=1, rfid_littlegate=0)
    assert record["rfid_gate"] == 1
    assert record["rfid_littlegate"] == 0


def test_list_returns_all_active_sorted_no_pagination(client: TestClient) -> None:
    a = _create(client, surname="Zebra", forename="Anna")
    b = _create(client, surname="Aaron", forename="Bob")

    # Filtračné query parametre sa ignorujú a nie je stránkovanie — vráti sa všetko.
    body = client.get(
        "/api/v1/employees", params={"surname": "nezmysel", "rfid_gate": 1, "page": 2}
    ).json()
    ids = [row["id"] for row in body["data"]]
    surnames = [row["surname"] for row in body["data"]]

    assert "pagination" not in body  # žiadne stránkovanie
    assert a["id"] in ids and b["id"] in ids  # filter aj page sa neuplatnili
    assert surnames == sorted(surnames)  # zoradené podľa priezviska (SQLite binárne)


def test_list_excludes_soft_deleted(client: TestClient, db_path: Path) -> None:
    record = _create(client, surname="SoonInactive")
    connection = sqlite3.connect(db_path)
    connection.execute("UPDATE er_reg_employees SET active = 0 WHERE id = ?", (record["id"],))
    connection.commit()
    connection.close()

    listing = client.get("/api/v1/employees").json()
    ids = [row["id"] for row in listing["data"]]
    assert record["id"] not in ids  # zmazaný (active=0) sa v zozname nezobrazí
    assert client.get(f"/api/v1/employees/{record['id']}").status_code == 404


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
