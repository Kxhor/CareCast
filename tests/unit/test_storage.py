"""Unit tests for T7–T11 database storage, AT-10, and AT-43 reproducibility (Phase 3)."""

import json
from datetime import date, timedelta
from pathlib import Path
import numpy as np
import pytest

from carecast.db import connect_rw, run_migrations
from carecast.pipeline import cmd_train


@pytest.fixture
def seeded_db(tmp_path: Path) -> Path:
    """Fixture providing a fresh database with migrations and 60 weeks of observations."""
    db_file = tmp_path / "test_carecast.db"
    run_migrations(db_file, "migrations")

    conn = connect_rw(db_file)
    try:
        # Seed dataset_sources
        conn.execute(
            """
            INSERT INTO dataset_sources
                (name, publisher, dataset_id, url, retrieved_at, file_name, file_sha256, row_count)
            VALUES ('cdc_nhsn_synthetic', 'CDC', 'ua7e-t2fy', 'https://example.com',
                    '2026-10-13T00:00:00Z', 'synthetic.csv',
                    '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef', 60);
            """
        )
        source_id = conn.execute("SELECT id FROM dataset_sources LIMIT 1;").fetchone()[0]

        # Seed 60 Saturday weeks of data for 'flu'
        # Satisfies Saturday check: strftime('%w', week_end_date) = '6'
        start_sat = date(2023, 1, 7)  # Saturday
        for i in range(60):
            sat_date = (start_sat + timedelta(weeks=i)).isoformat()
            # seasonal wave
            count = 100.0 + 40.0 * np.sin(i / 4.0)
            conn.execute(
                """
                INSERT INTO weekly_observations
                    (source_id, jurisdiction_code, disease_code, week_end_date, admissions_count,
                     admissions_rate_per_100k, pct_reporting)
                VALUES (?, 'US', 'flu', ?, ?, ?, 95.0);
                """,
                (source_id, sat_date, count, count / 10.0),
            )
        conn.commit()
    finally:
        conn.close()

    return db_file


def test_at_10_and_t7_t11_storage(seeded_db: Path) -> None:
    """AT-10 & Storage: Verify T7–T11 tables are properly populated with metrics, forecasts, intervals."""
    # Execute pipeline training on seeded database
    summary = cmd_train(db_path=seeded_db)
    assert "flu" in summary
    run_id_1 = summary["flu"]["run_id"]

    conn = connect_rw(seeded_db)
    try:
        # 1. Verify T7 model_runs
        run_row = conn.execute(
            "SELECT * FROM model_runs WHERE id = ?;", (run_id_1,)
        ).fetchone()
        assert run_row is not None
        assert run_row["is_current"] == 1
        assert run_row["jurisdiction_code"] == "US"
        assert run_row["disease_code"] == "flu"
        assert run_row["n_train"] > 0
        assert run_row["n_valid"] > 0
        assert run_row["n_test"] > 0

        # Verify config_json contains required provenance keys
        cfg_data = json.loads(run_row["config_json"])
        assert "config_hash" in cfg_data
        assert "library_versions" in cfg_data
        assert "scikit-learn" in cfg_data["library_versions"]
        assert "raw_file_sha256" in cfg_data
        assert "code_version" in cfg_data
        assert "clipping_notes" in cfg_data

        # 2. Verify T8 evaluation_metrics (AT-10)
        metrics = conn.execute(
            "SELECT * FROM evaluation_metrics WHERE run_id = ?;", (run_id_1,)
        ).fetchall()
        assert len(metrics) > 0

        # Check AT-10: interval_coverage on test block is computed, stored, and non-null for selected model
        test_selected = [
            m for m in metrics
            if m["is_selected"] == 1 and m["split"] == "test"
        ]
        assert len(test_selected) == 4  # 4 horizons

        for row in test_selected:
            cov = row["interval_coverage"]
            assert cov is not None, "AT-10 VIOLATION: interval_coverage is NULL on selected test metric!"
            assert 0.0 <= cov <= 1.0, f"Coverage out of bounds: {cov}"
            assert row["beats_persistence"] in (0, 1)

        # 3. Verify T9 backtest_predictions
        backtest = conn.execute(
            "SELECT COUNT(*) FROM backtest_predictions WHERE run_id = ?;", (run_id_1,)
        ).fetchone()[0]
        assert backtest > 0

        # 4. Verify T10 forecasts
        forecast_rows = conn.execute(
            "SELECT * FROM forecasts WHERE run_id = ? ORDER BY horizon_weeks;", (run_id_1,)
        ).fetchall()
        assert len(forecast_rows) == 4
        for fc in forecast_rows:
            assert fc["lower"] <= fc["point"] <= fc["upper"]
            assert fc["lower"] >= 0.0

        # 5. Verify T11 feature_contributions
        contrib_rows = conn.execute(
            "SELECT * FROM feature_contributions WHERE run_id = ?;", (run_id_1,)
        ).fetchall()
        assert len(contrib_rows) > 0
        feature_names = {c["feature_name"] for c in contrib_rows}
        assert "__base__" in feature_names

        # 6. Run train a second time to verify is_current flag rollover and AT-43 reproducibility
        summary2 = cmd_train(db_path=seeded_db)
        run_id_2 = summary2["flu"]["run_id"]
        assert run_id_2 != run_id_1

        # Previous run must now have is_current = 0
        old_run = conn.execute(
            "SELECT is_current FROM model_runs WHERE id = ?;", (run_id_1,)
        ).fetchone()
        assert old_run["is_current"] == 0

        new_run = conn.execute(
            "SELECT is_current FROM model_runs WHERE id = ?;", (run_id_2,)
        ).fetchone()
        assert new_run["is_current"] == 1

        # AT-43: Metrics between run 1 and run 2 must be bit-exact identical
        m1 = conn.execute(
            """
            SELECT horizon_weeks, model_name, split, mae, rmse, interval_coverage, beats_persistence
            FROM evaluation_metrics WHERE run_id = ?
            ORDER BY horizon_weeks, model_name, split;
            """,
            (run_id_1,),
        ).fetchall()

        m2 = conn.execute(
            """
            SELECT horizon_weeks, model_name, split, mae, rmse, interval_coverage, beats_persistence
            FROM evaluation_metrics WHERE run_id = ?
            ORDER BY horizon_weeks, model_name, split;
            """,
            (run_id_2,),
        ).fetchall()

        assert len(m1) == len(m2)
        for r1, r2 in zip(m1, m2):
            assert r1["horizon_weeks"] == r2["horizon_weeks"]
            assert r1["model_name"] == r2["model_name"]
            assert r1["split"] == r2["split"]
            assert abs(r1["mae"] - r2["mae"]) < 1e-12
            assert abs(r1["rmse"] - r2["rmse"]) < 1e-12
            assert r1["interval_coverage"] == r2["interval_coverage"]
            assert r1["beats_persistence"] == r2["beats_persistence"]
    finally:
        conn.close()
