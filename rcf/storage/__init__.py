"""RCF storage backends — SQLite persistence layer."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path("data/rcf.db")


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Get a SQLite connection with WAL mode and foreign keys enabled."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_schema(conn: sqlite3.Connection, schema_path: Path | str | None = None) -> None:
    """Initialize the database schema from schema.sql."""
    if schema_path is None:
        schema_path = Path(__file__).parent.parent.parent / "db" / "schema.sql"
    schema_sql = Path(schema_path).read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()


__all__ = ["get_connection", "init_schema"]
