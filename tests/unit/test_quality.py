"""Unit tests for quality checks module (carecast.quality)."""

import sqlite3
from pathlib import Path

from carecast.db import connect_rw, run_migrations
from carecast.quality import run_quality_checks


def test_quality_checks_gap_detection(tmp_path: Path) -> None:
    """Verify structural quality check detects gaps and flags long gaps (> 2 weeks)."""
    db_path = tmp_path / "quality_test.db"
    run_migrations(db_path, "migrations")

    conn = connect_rw(db_path)
    # Insert dummy source
    cur = conn.execute(
        """
        INSERT INTO dataset_sources
            (name, publisher, dataset_id, url, retrieved_at, file_name, file_sha256, row_count)
        VALUES ('test', 'test', 'test', 'http://test', '2024-01-01', 'test.csv',
                '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef', 10);
        """
    )
    source_id = cur.lastrowid

    # Insert observations with a 4-week gap between 2024-01-06 and 2024-02-03
    # Valid Saturdays: 2024-01-06, 2024-01-13 (missing), 2024-01-20 (missing), 2024-01-27 (missing), 2024-02-03
    conn.execute(
        """
        INSERT INTO weekly_observations
            (source_id, jurisdiction_code, disease_code, week_end_date, admissions_count, is_imputed)
        VALUES (?, 'US', 'flu', '2024-01-06', 100, 0);
        """,
        (source_id,),
    )
    conn.execute(
        """
        INSERT INTO weekly_observations
            (source_id, jurisdiction_code, disease_code, week_end_date, admissions_count, is_imputed)
        VALUES (?, 'US', 'flu', '2024-02-03', 120, 0);
        """,
        (source_id,),
    )
    conn.commit()

    issues = run_quality_checks(conn, source_id, jurisdiction_code="US", max_gap_weeks=2)
    conn.close()

    check_names = [i["check_name"] for i in issues]
    assert "missing_week" in check_names
    assert "long_gap" in check_names
