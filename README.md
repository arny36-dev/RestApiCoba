# Generic CRUD API

A production-ready FastAPI backend exposing **generic CRUD operations** over a
configurable whitelist of database tables. Table and column names are never
taken from user input directly — every table is validated against the
`ALLOWED_TABLES` whitelist and every column against reflected SQLAlchemy
metadata.

> ⚠️ **DELETE is soft delete only.** No endpoint ever issues a physical
> `DELETE`. The `DELETE` endpoint sets `active = 0` on the record. Tables
> without an `active` column cannot be deleted at all (the API returns `400`).

## Stack

- Python 3.12+, FastAPI, Uvicorn
- SQLAlchemy 2.x **async** with **Core** (no ORM models — tables are reflected
  at runtime)
- Pydantic v2 + pydantic-settings
- asyncpg (PostgreSQL)
- Pytest, Ruff, Alembic (prepared, no migrations generated)

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

Copy the example file and adjust it:

```bash
cp .env.example .env
```

| Variable | Required | Description |
| --- | --- | --- |
| `DATABASE_URL` | ✅ | Async SQLAlchemy URL, e.g. `postgresql+asyncpg://user:pass@host:5432/db` |
| `ALLOWED_TABLES` | ✅ | Comma-separated whitelist of tables the API may touch |
| `DEFAULT_PAGE_SIZE` | – | Default page size for listings (default `20`) |
| `MAX_PAGE_SIZE` | – | Hard upper bound for `page_size` (default `100`) |
| `API_PREFIX` | – | URL prefix for the CRUD API (default `/api/v1`) |
| `DEBUG` | – | `true` enables debug logging and error details in 500 responses |

### About `ALLOWED_TABLES`

`ALLOWED_TABLES` is the **security boundary** of this API. Only tables listed
there can be read or written — any other table name in the URL returns `404`.
Column names used in filters, sorting, inserts, and updates are additionally
validated against the table's real reflected schema, so neither table nor
column identifiers from a request ever reach SQL unchecked.

```env
ALLOWED_TABLES=er_reg_employees,er_reg_employee_emails,er_reg_employee_bozp_files,er_reg_employee_types
```

## Running the app

```bash
uvicorn app.main:app --reload
```

Interactive docs: <http://127.0.0.1:8000/docs>

## Running tests

Tests run against a temporary SQLite database (via `aiosqlite`) — no
PostgreSQL needed:

```bash
pytest
```

## Running Ruff

```bash
ruff check .
ruff format --check .
```

## API overview

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/tables` | List whitelisted tables |
| `GET` | `/api/v1/{table}/metadata` | Reflected column metadata |
| `GET` | `/api/v1/{table}` | List records (filters, pagination, sorting) |
| `GET` | `/api/v1/{table}/{id}` | Get one record |
| `POST` | `/api/v1/{table}` | Create a record |
| `PUT` | `/api/v1/{table}/{id}` | Update provided fields |
| `PATCH` | `/api/v1/{table}/{id}` | Update provided fields |
| `DELETE` | `/api/v1/{table}/{id}` | **Soft delete** (`active = 0`) |

### Listing behavior

- `page` (default `1`), `page_size` (default `DEFAULT_PAGE_SIZE`, values above
  `MAX_PAGE_SIZE` are **clamped** to it), `sort` + `order` (`asc`/`desc`).
- If the table has an `active` column, only `active = 1` rows are returned
  unless `include_inactive=true`.
- Any other query parameter is treated as a filter and must match a real
  column, otherwise the API returns `422`:
  - text columns → case-insensitive partial match
  - integer / numeric / boolean columns → exact match
  - date / datetime columns → `{field}_from` and `{field}_to` range filters

### Write behavior

- Unknown columns are rejected with `422`.
- Auto-generated primary keys cannot be written; the primary key can never be
  changed.
- On create, `active` defaults to `1` and `created` / `created_at` /
  `modified` / `updated_at` are stamped if those columns exist.
- On update and soft delete, `modified` / `updated_at` are stamped if present.
- Only single-column primary keys are supported; composite keys return `400`.

## Example curl requests

List tables:

```bash
curl http://127.0.0.1:8000/api/v1/tables
```

Get metadata:

```bash
curl http://127.0.0.1:8000/api/v1/er_reg_employees/metadata
```

List records with filters (partial name match, exact type, date range, paging):

```bash
curl "http://127.0.0.1:8000/api/v1/er_reg_employees?surname=smith&employee_type_id=2&created_from=2024-01-01&page=1&page_size=20&sort=surname&order=asc"
```

Create a record:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/er_reg_employees \
  -H "Content-Type: application/json" \
  -d '{"forename": "John", "surname": "Smith", "active": 1}'
```

PUT update:

```bash
curl -X PUT http://127.0.0.1:8000/api/v1/er_reg_employees/123 \
  -H "Content-Type: application/json" \
  -d '{"forename": "John", "surname": "Smith-Jones"}'
```

PATCH update:

```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/er_reg_employees/123 \
  -H "Content-Type: application/json" \
  -d '{"surname": "Smith-Jones"}'
```

Soft delete:

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/er_reg_employees/123
```

Response:

```json
{ "status": "deleted", "id": 123 }
```

## Error format

All errors use a consistent shape:

```json
{ "detail": "Clear error message" }
```

Stack traces are never exposed; with `DEBUG=false`, unexpected errors return a
generic `{"detail": "Internal server error"}`.

## Migrations (Alembic)

Alembic is installed and `alembic.ini` is prepared, but **no migrations are
generated** — the real schema is owned by the existing database and tables are
reflected at runtime. When you take ownership of the schema, run
`alembic init migrations` and wire `migrations/env.py` to read `DATABASE_URL`
from the environment.

## Limitations / assumptions

- Only single-column primary keys are supported (`400` otherwise).
- A table literally named `tables` would be shadowed by the `/tables` route.
- `page_size` above `MAX_PAGE_SIZE` is clamped, not rejected (documented,
  consistent behavior).
- Reflected metadata is cached for the process lifetime; restart the app after
  changing a table's schema.
