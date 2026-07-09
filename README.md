# RestApiCoba — Employees API

FastAPI backend exposing **explicit employee endpoints** over the legacy
`pv31` database (MariaDB), replacing the old CakePHP `Employees.ErRegEmployees`
operations. There are **no dynamic table routes** — every endpoint reads or
writes fixed, known tables only:

- `er_reg_employees` — read/write (the only writable table)
- `er_reg_employee_types` — read-only listing

> ⚠️ **DELETE is soft delete only.** No endpoint ever issues a physical
> `DELETE`. The `DELETE` endpoint sets `active = 0` on the employee.

## Stack

- Python 3.12+, FastAPI, Uvicorn
- SQLAlchemy 2.x **async** with **Core** (tables reflected at runtime)
- aiomysql (MariaDB/MySQL) / asyncpg (PostgreSQL)
- Pydantic v2 + pydantic-settings, Pytest, Ruff

## Installation

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -e ".[dev]"
```

## Configuration — create `.env`

```bash
cp .env.example .env
```

| Variable | Required | Description |
| --- | --- | --- |
| `DATABASE_URL` | ✅ | Async SQLAlchemy URL. MariaDB/MySQL: `mysql+aiomysql://user:pass@host:3306/db?charset=utf8mb4` |
| `DEFAULT_OBJECT_ID` | – | Fallback `object_id` used for filtering and creating employees |
| `DEFAULT_PAGE_SIZE` | – | Default page size for listings (default `20`) |
| `MAX_PAGE_SIZE` | – | Hard upper bound for `page_size`; larger values return `422` |
| `API_PREFIX` | – | URL prefix (default `/api/v1`) |
| `DEBUG` | – | `true` enables debug logging and error details in 500 responses |
| `LOG_DIR` | – | Log directory (default `logs`) |

## Running the app

```bash
uvicorn app.main:app --reload
```

Interactive docs: <http://127.0.0.1:8000/docs>

At startup the app logs the **safe** DB config (dialect, host, port, database,
user — never the password).

## Running tests / Ruff

```bash
pytest
ruff check .
ruff format --check .
```

Tests run against a temporary SQLite database mirroring the real schema — no
MariaDB needed.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | App liveness |
| `GET` | `/api/v1/db/health` | Real DB check (`SELECT 1`); 503 with safe message on failure |
| `GET` | `/api/v1/employees` | List employees (filters + pagination, always `active = 1`) |
| `GET` | `/api/v1/employees/{id}` | Employee detail (404 if missing or inactive) |
| `POST` | `/api/v1/employees` | Create employee |
| `PUT` | `/api/v1/employees/{id}` | Update editable fields |
| `PATCH` | `/api/v1/employees/{id}` | Update provided fields |
| `DELETE` | `/api/v1/employees/{id}` | **Soft delete** (`active = 0`) |
| `GET` | `/api/v1/employee-types` | Read-only active employee types |

### Listing filters

`forename`, `surname`, `type`, `rfid`, `ecv`, `note`, `bozp_state` — partial,
case-insensitive match (like the old CakePHP code). `rfid_gate` and
`rfid_littlegate` accept `0`, `1`, or `2` (= all, no filter). `object_id`
defaults to `DEFAULT_OBJECT_ID`. Sort is fixed: `surname ASC, forename ASC`.

### Write rules

- `surname` is required on create; unknown fields are rejected with `422`.
- `id` and `active` can never be written through POST/PUT/PATCH.
- On create the API sets `active = 1`, `bozp_state = 'NO BOZP'`,
  `bozp_required = 0` and stamps `created`/`modified`.
  (Note: the real column is `bozp_state`, an ENUM whose "no training" value is
  `'NO BOZP'` — there is no `bozp_status` column.)
- On update and soft delete `modified` is stamped.

## Example curl requests

```bash
curl -i "http://127.0.0.1:8000/health"
curl -i "http://127.0.0.1:8000/api/v1/db/health"
curl -i "http://127.0.0.1:8000/api/v1/employees?page=1&page_size=5"
curl -i "http://127.0.0.1:8000/api/v1/employees?surname=smith&rfid_gate=2"
curl -i "http://127.0.0.1:8000/api/v1/employees/123"
curl -i -X POST "http://127.0.0.1:8000/api/v1/employees" \
  -H "Content-Type: application/json" \
  -d '{"forename": "John", "surname": "Smith", "type": "employee", "rfid_gate": 1}'
curl -i -X PATCH "http://127.0.0.1:8000/api/v1/employees/123" \
  -H "Content-Type: application/json" -d '{"note": "updated"}'
curl -i -X DELETE "http://127.0.0.1:8000/api/v1/employees/123"
curl -i "http://127.0.0.1:8000/api/v1/employee-types"
```

## Logging

Logs are written to the console **and** `logs/app.log` (rotating, 10 MB × 5
backups) in **simple Slovak**, one line per event, saying exactly what
happened:

```text
07.07.2026 15:10:02 | INFO | Vytvorený nový zamestnanec ID 351: Smith John
07.07.2026 15:10:05 | INFO | GET /api/v1/employees?surname=smith → 200 (v poriadku, 38 ms)
07.07.2026 15:10:09 | POZOR | DELETE /api/v1/employees/999 → 404 (nenájdené) | dôvod: Zamestnanec 999 neexistuje alebo je neaktívny
```

Technical library noise (SQL statements, driver chatter) is hidden by
default — set `LOG_SQL=true` in `.env` to log every SQL statement while
debugging. Unexpected errors log the full traceback to the file; clients never
see it.

## Error format

```json
{ "detail": "Clear error message" }
```
