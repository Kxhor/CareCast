"""Unit tests for data ingestion (Phase 2, AT-01, AT-02, AT-03, AT-04)."""

import hashlib
import sqlite3
from pathlib import Path
import pytest

from carecast.db import connect_ro, run_migrations
from carecast.ingest import ingest_csv


def _setup_test_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.db"
    run_migrations(db_path, "migrations")
    return db_path


def test_at_01_ingest_idempotency(tmp_path: Path) -> None:
    """AT-01: Running ingest twice yields identical row counts (2nd run inserts 0)."""
    db_path = _setup_test_db(tmp_path)
    csv_path = Path("tests/fixtures/sample_valid.csv")

    res1 = ingest_csv(csv_path, db_path=db_path)
    assert res1["rows_inserted"] > 0
    assert not res1["already_ingested"]

    conn = connect_ro(db_path)
    count1 = conn.execute("SELECT COUNT(*) FROM weekly_observations;").fetchone()[0]
    conn.close()

    res2 = ingest_csv(csv_path, db_path=db_path)
    assert res2["rows_inserted"] == 0
    assert res2["already_ingested"]

    conn = connect_ro(db_path)
    count2 = conn.execute("SELECT COUNT(*) FROM weekly_observations;").fetchone()[0]
    conn.close()

    assert count1 == count2


def test_at_02_missing_column_aborts(tmp_path: Path) -> None:
    """AT-02: CSV with missing/renamed required column aborts with an error."""
    db_path = _setup_test_db(tmp_path)
    csv_path = Path("tests/fixtures/sample_missing_col.csv")

    with pytest.raises(ValueError, match="Required columns absent from CSV"):
        ingest_csv(csv_path, db_path=db_path)


def test_at_03_defects_detected_and_logged(tmp_path: Path) -> None:
    """AT-03: Injected duplicate, gap, negative, non-Saturday date are each detected and logged to T6."""
    db_path = _setup_test_db(tmp_path)
    csv_path = Path("tests/fixtures/sample_defects.csv")

    res = ingest_csv(csv_path, db_path=db_path)
    assert res["quality_issues_logged"] > 0

    conn = connect_ro(db_path)
    issues = [
        r["check_name"]
        for r in conn.execute("SELECT check_name FROM data_quality_issues;").fetchall()
    ]
    conn.close()

    assert "duplicate_key" in issues
    assert "non_saturday" in issues
    assert "negative_value" in issues
    assert "non_numeric" in issues
    assert "coverage_out_of_range" in issues
    assert "missing_week" in issues or "long_gap" in issues


def test_at_04_raw_file_sha256_recorded(tmp_path: Path) -> None:
    """AT-04: Raw file SHA-256 recorded in dataset_sources; file unchanged after run."""
    db_path = _setup_test_db(tmp_path)
    csv_path = Path("tests/fixtures/sample_valid.csv")

    sha_before = hashlib.sha256(csv_path.read_bytes()).hexdigest()

    res = ingest_csv(csv_path, db_path=db_path)

    sha_after = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    assert sha_before == sha_after

    conn = connect_ro(db_path)
    recorded = conn.execute(
        "SELECT file_sha256 FROM dataset_sources WHERE id = ?;",
        (res["source_id"],),
    ).fetchone()[0]
    conn.close()

    assert recorded == sha_before
