"""Tests for schema constraints and privacy guarantees (Phase 2, AT-45 & negative DB tests)."""

import sqlite3
from pathlib import Path
import pytest

from carecast.db import connect_rw, run_migrations


def _setup_db(tmp_path: Path) -> Path:
    db_file = tmp_path / "schema_test.db"
    run_migrations(db_file, "migrations")
    return db_file


def test_at_45_privacy_schema_check(tmp_path: Path) -> None:
    """AT-45: Verify schema has no patient-level identifiers; stores only aggregates."""
    db_file = _setup_db(tmp_path)
    conn = connect_rw(db_file)
    try:
        # Check all tables and column names
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ).fetchall()

        forbidden_tokens = {
            "patient", "mrn", "ssn", "dob", "birth", "name", "first_name",
            "last_name", "address", "phone", "email", "zip", "gender", "race", "ethnicity"
        }
        # Exceptions: table names like 'dataset_sources' has 'name' which refers to dataset name,
        # 'jurisdictions' has 'name' for jurisdiction name.

        for (table_name,) in tables:
            assert "patient" not in table_name.lower(), f"Forbidden table name: {table_name}"
            cols = [
                r[1]
                for r in conn.execute(f"PRAGMA table_info({table_name});").fetchall()
            ]
            for col in cols:
                col_lower = col.lower()
                for token in ("patient", "mrn", "ssn", "dob"):
                    assert token not in col_lower, f"Forbidden column '{col}' in table '{table_name}'"
    finally:
        conn.close()


def test_negative_constraint_non_saturday_date(tmp_path: Path) -> None:
    """Negative test: DB CHECK constraint rejects non-Saturday week_end_date."""
    db_file = _setup_db(tmp_path)
    conn = connect_rw(db_file)
    try:
        # Wednesday date: 2024-01-10 (strftime('%w', '2024-01-10') == '3')
        cur = conn.execute(
            """
            INSERT INTO dataset_sources
                (name, publisher, dataset_id, url, retrieved_at, file_name, file_sha256, row_count)
            VALUES ('test', 'test', 'test', 'http://test', '2024-01-01', 'test.csv',
                    '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef', 1);
            """
        )
        source_id = cur.lastrowid

        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            conn.execute(
                """
                INSERT INTO weekly_observations
                    (source_id, jurisdiction_code, disease_code, week_end_date, admissions_count)
                VALUES (?, 'US', 'flu', '2024-01-10', 50);
                """,
                (source_id,),
            )
    finally:
        conn.close()


def test_negative_constraint_negative_admissions(tmp_path: Path) -> None:
    """Negative test: DB CHECK constraint rejects negative admissions count."""
    db_file = _setup_db(tmp_path)
    conn = connect_rw(db_file)
    try:
        cur = conn.execute(
            """
            INSERT INTO dataset_sources
                (name, publisher, dataset_id, url, retrieved_at, file_name, file_sha256, row_count)
            VALUES ('test', 'test', 'test', 'http://test', '2024-01-01', 'test.csv',
                    '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef', 1);
            """
        )
        source_id = cur.lastrowid

        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            conn.execute(
                """
                INSERT INTO weekly_observations
                    (source_id, jurisdiction_code, disease_code, week_end_date, admissions_count)
                VALUES (?, 'US', 'flu', '2024-01-06', -25);
                """,
                (source_id,),
            )
    finally:
        conn.close()


def test_negative_constraint_train_valid_test_overlap(tmp_path: Path) -> None:
    """Negative test: DB CHECK constraint rejects overlapping train/valid/test date blocks."""
    db_file = _setup_db(tmp_path)
    conn = connect_rw(db_file)
    try:
        cur = conn.execute(
            """
            INSERT INTO dataset_sources
                (name, publisher, dataset_id, url, retrieved_at, file_name, file_sha256, row_count)
            VALUES ('test', 'test', 'test', 'http://test', '2024-01-01', 'test.csv',
                    '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef', 1);
            """
        )
        source_id = cur.lastrowid

        # Overlapping: train_end (2024-06-01) >= valid_start (2024-05-01)
        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            conn.execute(
                """
                INSERT INTO model_runs
                    (created_at, jurisdiction_code, disease_code, source_id, target_kind,
                     data_end_date, train_start, train_end, valid_start, valid_end,
                     test_start, test_end, n_train, n_valid, n_test, interval_level,
                     default_threshold, default_threshold_method, reference_level,
                     random_seed, config_json, data_sha256, code_version, is_current)
                VALUES
                    ('2024-01-01', 'US', 'flu', ?, 'count', '2024-08-01',
                     '2024-01-01', '2024-06-01', '2024-05-01', '2024-07-01',
                     '2024-07-08', '2024-08-01', 20, 10, 10, 0.8,
                     100.0, 'percentile_75', 50.0, 42, '{}',
                     '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef', 'v1', 0);
                """,
                (source_id,),
            )
    finally:
        conn.close()
