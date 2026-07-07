"""Shared test fixtures: the app wired to a temporary SQLite database.

The schema is created with the stdlib ``sqlite3`` module (synchronously, before
any event loop exists) and the app talks to it through ``sqlite+aiosqlite``.
"""

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SCHEMA = """
CREATE TABLE items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    quantity INTEGER,
    active INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME,
    updated_at DATETIME
);
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    body VARCHAR(255) NOT NULL
);
"""


@pytest.fixture(scope="session")
def client(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    db_path: Path = tmp_path_factory.mktemp("db") / "test.db"
    connection = sqlite3.connect(db_path)
    connection.executescript(SCHEMA)
    connection.commit()
    connection.close()

    os.environ.update(
        {
            "APP_NAME": "Generic CRUD API (tests)",
            "APP_ENV": "test",
            "DEBUG": "false",
            "DATABASE_URL": f"sqlite+aiosqlite:///{db_path.as_posix()}",
            "ALLOWED_TABLES": "items,notes",
            "DEFAULT_PAGE_SIZE": "10",
            "MAX_PAGE_SIZE": "50",
        }
    )

    from app.core.config import get_settings

    get_settings.cache_clear()

    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
