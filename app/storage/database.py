"""SQLite connection and schema for local, non-secret application state."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.utils.paths import roaming_data_directory


SCHEMA = """
CREATE TABLE IF NOT EXISTS favorites (
    did TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


def default_database_path() -> Path:
    return roaming_data_directory() / "mijia-desktop.db"


def open_database(path: Path | None = None) -> sqlite3.Connection:
    database_path = path or default_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.execute(SCHEMA)
    connection.commit()
    return connection
