"""Tests for the RCF storage module — SQLite persistence layer."""

import sqlite3
import tempfile
from pathlib import Path

from rcf.storage import get_connection, init_schema


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


def test_import_storage():
    """The rcf.storage module is importable and exposes key symbols."""
    import rcf.storage

    assert hasattr(rcf.storage, "get_connection")
    assert hasattr(rcf.storage, "init_schema")


# ---------------------------------------------------------------------------
# get_connection
# ---------------------------------------------------------------------------


def test_get_connection_creates_db():
    """get_connection creates a SQLite file with WAL mode and foreign keys."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        assert not db_path.exists()

        conn = get_connection(db_path)
        assert db_path.exists()

        # Verify WAL mode
        row = conn.execute("PRAGMA journal_mode").fetchone()
        assert row[0].lower() == "wal"

        # Verify foreign keys enabled
        row = conn.execute("PRAGMA foreign_keys").fetchone()
        assert row[0] == 1

        conn.close()


# ---------------------------------------------------------------------------
# init_schema
# ---------------------------------------------------------------------------


def test_init_schema_creates_tables():
    """init_schema creates all required tables from schema.sql."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        conn = get_connection(db_path)

        # Point to the project's schema.sql
        schema_path = Path(__file__).parent.parent / "db" / "schema.sql"
        assert schema_path.exists(), f"schema.sql not found at {schema_path}"

        init_schema(conn, schema_path)

        # Check core tables exist
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}

        expected_tables = {
            "companies",
            "contacts",
            "emails",
            "phones",
            "sources",
            "arabic_name_cache",
            "sessions",
            "search_results",
            "api_usage",
            "tags",
            "exports",
            "known_email_patterns",
        }
        for table in expected_tables:
            assert table in tables, f"Missing table: {table}"

        conn.close()
