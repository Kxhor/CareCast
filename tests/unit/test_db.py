"""Unit tests for database connection modes and query enforcement."""

from pathlib import Path
import sqlite3
import pytest

from carecast.db import connect_ro, connect_rw, run_migrations


def test_connect_rw_creates_and_writes(tmp_path: Path) -> None:
    """Verify connect_rw allows table creation and row insertion."""
    db_file = tmp_path / "rw_test.db"
    conn = connect_rw(db_file)
    try:
        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT);")
        conn.execute("INSERT INTO items (name) VALUES ('influenza');")
        conn.commit()

        cursor = conn.execute("SELECT name FROM items;")
        row = cursor.fetchone()
        assert row is not None
        assert row["name"] == "influenza"
    finally:
        conn.close()


def test_connect_ro_enforces_read_only(tmp_path: Path) -> None:
    """Verify connect_ro allows queries but rejects write operations."""
    db_file = tmp_path / "ro_test.db"
    # Seed with rw
    seed_conn = connect_rw(db_file)
    seed_conn.execute("CREATE TABLE series (id TEXT PRIMARY KEY, val REAL);")
    seed_conn.execute("INSERT INTO series VALUES ('flu', 42.0);")
    seed_conn.commit()
    seed_conn.close()

    # Open read-only
    ro_conn = connect_ro(db_file)
    try:
        # Read operation succeeds
        row = ro_conn.execute("SELECT val FROM series WHERE id = 'flu';").fetchone()
        assert row is not None
        assert row["val"] == 42.0

        # Write operations fail with OperationalError
        with pytest.raises(sqlite3.OperationalError):
            ro_conn.execute("INSERT INTO series VALUES ('rsv', 10.0);")

        with pytest.raises(sqlite3.OperationalError):
            ro_conn.execute("UPDATE series SET val = 50.0 WHERE id = 'flu';")

        with pytest.raises(sqlite3.OperationalError):
            ro_conn.execute("CREATE TABLE new_tbl (x INT);")
    finally:
        ro_conn.close()


def test_connect_ro_missing_file_raises(tmp_path: Path) -> None:
    """Verify FileNotFoundError when connecting read-only to non-existent database."""
    missing = tmp_path / "does_not_exist.db"
    with pytest.raises(FileNotFoundError):
        connect_ro(missing)


def test_migration_runner_skeleton(tmp_path: Path) -> None:
    """Verify migration runner applies SQL scripts in forward order."""
    db_file = tmp_path / "mig_test.db"
    mig_dir = tmp_path / "migrations"
    mig_dir.mkdir()

    (mig_dir / "0001_initial.sql").write_text(
        "CREATE TABLE test1 (id INT PRIMARY KEY);", encoding="utf-8"
    )
    (mig_dir / "0002_second.sql").write_text(
        "CREATE TABLE test2 (val TEXT);", encoding="utf-8"
    )

    applied = run_migrations(db_file, mig_dir)
    assert applied == ["0001_initial", "0002_second"]

    # Re-running applies zero new migrations
    second_run = run_migrations(db_file, mig_dir)
    assert second_run == []
