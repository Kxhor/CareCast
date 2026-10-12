"""Tests for schema migrations and database structure (Phase 2)."""

from pathlib import Path
import pytest

from carecast.db import connect_ro, connect_rw, run_migrations


def test_migrations_fresh_db(tmp_path: Path) -> None:
    """Verify applying migrations to a fresh DB creates all expected tables."""
    db_file = tmp_path / "fresh.db"
    applied = run_migrations(db_file, "migrations")
    assert applied == ["0001_core_data", "0002_forecasting"]

    # Verify tables and seeds via read-only connection
    conn = connect_ro(db_file)
    try:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view');"
            ).fetchall()
        }
        expected = {
            "schema_migrations",
            "dataset_sources",
            "jurisdictions",
            "diseases",
            "weekly_observations",
            "data_quality_issues",
            "model_runs",
            "evaluation_metrics",
            "backtest_predictions",
            "forecasts",
            "feature_contributions",
            "v_current_runs",
        }
        assert expected.issubset(tables)

        # Check seeded diseases and jurisdictions
        diseases = [r["code"] for r in conn.execute("SELECT code FROM diseases ORDER BY code;").fetchall()]
        assert diseases == ["covid19", "flu", "rsv"]

        jurisdictions = [r["code"] for r in conn.execute("SELECT code FROM jurisdictions;").fetchall()]
        assert "US" in jurisdictions
    finally:
        conn.close()


def test_migrations_idempotency(tmp_path: Path) -> None:
    """Verify running migrations a second time applies zero changes."""
    db_file = tmp_path / "idempotent.db"
    first = run_migrations(db_file, "migrations")
    assert len(first) == 2

    second = run_migrations(db_file, "migrations")
    assert second == []
