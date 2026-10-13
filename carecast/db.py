"""CareCast database connectivity and schema migrations.

Provides read-write (connect_rw) and read-only (connect_ro) SQLite connections.
connect_ro enforces SQLite URI mode=ro, PRAGMA query_only=ON, and PRAGMA foreign_keys=ON.
Conforms to TRD §4, §8, §9 and BACKEND_SCHEMA §1, §3.
"""

from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Sequence


def connect_rw(db_path: Path | str = "data/carecast.db") -> sqlite3.Connection:
    """Create a read-write SQLite connection with foreign keys enabled.
    
    Ensures parent directories exist before connecting.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def connect_ro(db_path: Path | str = "data/carecast.db") -> sqlite3.Connection:
    """Create a strictly read-only SQLite connection.
    
    Enforces:
    1. URI mode=ro
    2. PRAGMA query_only = ON
    3. PRAGMA foreign_keys = ON
    
    Any write attempt will raise sqlite3.OperationalError.
    """
    path = Path(db_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Database file does not exist: {path}")
    
    uri = f"file:{path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def run_migrations(
    db_path: Path | str = "data/carecast.db",
    migrations_dir: Path | str = "migrations",
) -> list[str]:
    """Execute pending SQL migrations in forward order within individual transactions.
    
    Skips migrations already recorded in schema_migrations.
    Returns the list of migration versions applied during this invocation.
    """
    mig_dir = Path(migrations_dir)
    if not mig_dir.exists():
        return []

    sql_files = sorted(mig_dir.glob("*.sql"))
    if not sql_files:
        return []

    applied_now: list[str] = []
    conn = connect_rw(db_path)
    try:
        # Check if schema_migrations table exists
        has_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations';"
        ).fetchone()

        if has_table:
            existing_rows = conn.execute("SELECT version FROM schema_migrations;").fetchall()
            applied_set = {row["version"] for row in existing_rows}
        else:
            applied_set = set()

        for sql_file in sql_files:
            version_stem = sql_file.stem
            version_name = sql_file.name

            # Skip if either stem or filename was already recorded
            if version_stem in applied_set or version_name in applied_set:
                continue

            with open(sql_file, "r", encoding="utf-8") as f:
                script = f.read()

            # Execute migration in a single transaction per file
            with conn:
                conn.executescript(script)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version    TEXT PRIMARY KEY,
                        applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
                    );
                    """
                )
                conn.execute(
                    "INSERT OR IGNORE INTO schema_migrations (version) VALUES (?);",
                    (version_stem,),
                )
            applied_now.append(version_stem)
            applied_set.add(version_stem)
            applied_set.add(version_name)

    finally:
        conn.close()

    return applied_now
