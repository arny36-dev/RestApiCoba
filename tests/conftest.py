"""Shared test fixtures: the app wired to a temporary SQLite database.

The schema mirrors the real ``pv31`` tables (er_reg_employees,
er_reg_employee_types). It is created with the stdlib ``sqlite3`` module and
the app talks to it through ``sqlite+aiosqlite``.
"""

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Valid API key used by the default authenticated test client.
TEST_API_KEY = "test-api-key-1234567890"

SCHEMA = """
CREATE TABLE er_reg_employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id INTEGER,
    forename VARCHAR(50),
    surname VARCHAR(50) NOT NULL,
    type VARCHAR(50),
    rfid VARCHAR(50),
    rfid_gate TINYINT NOT NULL DEFAULT 0,
    rfid_littlegate TINYINT NOT NULL DEFAULT 0,
    ecv VARCHAR(50),
    allowed_from DATETIME,
    allowed_to DATETIME,
    note VARCHAR(200),
    row_id CHAR(36),
    created TIMESTAMP,
    modified TIMESTAMP,
    active TINYINT DEFAULT 1,
    bozp_required TINYINT DEFAULT 0,
    bozp_state VARCHAR(30) DEFAULT 'NO BOZP'
);
CREATE TABLE er_reg_employee_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255),
    created_at TIMESTAMP,
    modified_at TIMESTAMP,
    active TINYINT DEFAULT 1,
    object_id INTEGER,
    row_id CHAR(36)
);
INSERT INTO er_reg_employee_types (name, active, object_id) VALUES
    ('employee', 1, 127),
    ('visitor', 1, 127),
    ('inactive type', 0, 127),
    ('other object type', 1, 999);
"""


@pytest.fixture(scope="session")
def db_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path: Path = tmp_path_factory.mktemp("db") / "test.db"
    connection = sqlite3.connect(path)
    connection.executescript(SCHEMA)
    connection.commit()
    connection.close()
    return path


@pytest.fixture(scope="session")
def client(db_path: Path) -> Iterator[TestClient]:
    os.environ.update(
        {
            "APP_NAME": "RestApiCoba (tests)",
            "APP_ENV": "test",
            "DEBUG": "false",
            "DATABASE_URL": f"sqlite+aiosqlite:///{db_path.as_posix()}",
            "API_KEY": TEST_API_KEY,
            "DEFAULT_OBJECT_ID": "127",
            "DEFAULT_PAGE_SIZE": "10",
            "MAX_PAGE_SIZE": "50",
        }
    )

    from app.core.config import get_settings

    get_settings.cache_clear()

    from app.main import create_app

    # Default client is authenticated: it sends a valid key on every request so
    # the existing endpoint tests exercise behaviour, not auth. Tests that check
    # auth itself build their own unauthenticated client below.
    with TestClient(create_app(), headers={"X-API-Key": TEST_API_KEY}) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def anon_client(db_path: Path, client: TestClient) -> TestClient:
    """Client without the API key, for testing 401 responses.

    Depends on ``client`` so the environment and app are already configured.
    """
    from app.main import create_app

    return TestClient(create_app())
