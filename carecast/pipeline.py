"""CLI pipeline orchestrator (Phase 2/3).

Supports:
- migrate: run DB schema migrations
- ingest: parse and validate CDC CSV dataset
- train: train models, evaluate walk-forward, persist forecasts & explainability
- check: display data quality report from data_quality_issues
- rebuild: run migrate, then ingest, then train
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn

import carecast
from carecast.db import connect_ro, connect_rw, run_migrations
from carecast.evaluate import evaluate_horizon
from carecast.explain import compute_linear_contributions, compute_permutation_importance
from carecast.features import build_feature_row, create_dataset_for_horizon
from carecast.ingest import ingest_csv
from carecast.models import LinearLagModel, get_model
from carecast.settings import get_settings

logger = logging.getLogger("carecast.pipeline")


def cmd_migrate(db_path: Path | str | None = None, migrations_dir: Path | str = "migrations") -> list[str]:
    """Execute forward database migrations."""
    if db_path is None:
        db_path = get_settings().db_path
    print(f"--> Running migrations on {db_path} from {migrations_dir}...")
    applied = run_migrations(db_path, migrations_dir)
    if applied:
        print(f"[OK] Applied migrations: {', '.join(applied)}")
    else:
        print("[OK] Schema is up to date (0 new migrations).")
    return applied


def cmd_ingest(
    csv_path: Path | str | None = None,
    db_path: Path | str | None = None,
    mapping_path: Path | str = "config/dataset_mapping.toml",
) -> dict[str, Any]:
    """Ingest CDC CSV dataset into SQLite."""
    if db_path is None:
        db_path = get_settings().db_path

    if csv_path is None:
        raw_candidates = [
            Path("data/raw/ua7e-t2fy.csv"),
            Path("data/raw/Weekly_Hospital_Respiratory_Data__HRD__Metrics_by_Jurisdiction__National_Healthcare_Safety_Network__NHSN_.csv"),
        ]
        found = [p for p in raw_candidates if p.exists()]
        if not found:
            all_raw = list(Path("data/raw").glob("*.csv"))
            if all_raw:
                found = all_raw
        if not found:
            raise FileNotFoundError("No raw CSV file specified and none found in data/raw/.")
        csv_path = found[0]

    print(f"--> Ingesting {csv_path} into {db_path}...")
    result = ingest_csv(csv_path, db_path, mapping_path)
    if result.get("already_ingested"):
        print(f"[OK] Already ingested (source_id={result['source_id']}). Added 0 rows.")
    else:
        print(
            f"[OK] Ingestion complete: source_id={result['source_id']}, "
            f"inserted={result['rows_inserted']}, skipped={result['rows_skipped']}, "
            f"quality_issues={result['quality_issues_logged']}"
        )
    return result


def cmd_train(
    db_path: Path | str | None = None,
    config_path: Path | str = "config/pipeline.toml",
) -> dict[str, Any]:
    """Train models, evaluate walk-forward, persist T7–T11 (Phase 3)."""
    if db_path is None:
        db_path = get_settings().db_path
    cfg_file = Path(config_path)
    if not cfg_file.exists():
        raise FileNotFoundError(f"Pipeline configuration not found: {cfg_file}")

    with cfg_file.open("rb") as f:
        cfg = tomllib.load(f)

    cfg_bytes = cfg_file.read_bytes()
    config_hash = hashlib.sha256(cfg_bytes).hexdigest()

    try:
        git_bin = shutil.which("git")
        if git_bin:
            git_commit = subprocess.check_output(  # nosec B603
                [git_bin, "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
            ).strip()
        else:
            git_commit = "unknown"
    except Exception:
        git_commit = "unknown"

    conn = connect_rw(db_path)
    results_summary: dict[str, Any] = {}

    try:
        source_row = conn.execute(
            "SELECT id, file_sha256 FROM dataset_sources ORDER BY id DESC LIMIT 1;"
        ).fetchone()
        if not source_row:
            raise RuntimeError("No ingested dataset found in dataset_sources. Run ingest first.")
        source_id = source_row["id"]
        raw_sha256 = source_row["file_sha256"]

        horizons = cfg["forecast"]["horizons"]
        interval_level = cfg["forecast"]["interval_level"]
        random_seed = cfg["forecast"]["random_seed"]
        threshold_pct = cfg["forecast"]["threshold_percentile"]
        threshold_method = cfg["forecast"]["threshold_method"]

        baselines = cfg["models"]["baselines"]
        candidates = cfg["models"]["candidates"]

        disease_starts = cfg["data"].get("disease_training_start", {})
        default_start = cfg["data"]["training_start"]

        for disease in ("flu", "covid19", "rsv"):
            print(f"\n--> Training & Evaluating series: {disease.upper()} (US)...")
            start_date = disease_starts.get(disease, default_start)

            # Fetch observations in chronological order
            rows = conn.execute(
                """
                SELECT week_end_date, admissions_count, admissions_rate_per_100k, pct_reporting
                FROM weekly_observations
                WHERE jurisdiction_code = 'US' AND disease_code = ? AND week_end_date >= ?
                ORDER BY week_end_date ASC;
                """,
                (disease, start_date),
            ).fetchall()

            if len(rows) < 20:
                print(f"[SKIP] Insufficient observations ({len(rows)}) for {disease} from {start_date}.")
                continue

            obs_data = [dict(r) for r in rows]
            df = pd.DataFrame(obs_data)

            # Check if 52 weeks precede for seasonal_lag52
            history_rows = conn.execute(
                """
                SELECT COUNT(*) FROM weekly_observations
                WHERE jurisdiction_code = 'US' AND disease_code = ?;
                """,
                (disease,),
            ).fetchone()[0]
            include_seasonal_52 = (history_rows >= 70) and cfg["features"]["include_seasonal_lag52"]

            # Filter active baselines (only include seasonal_naive if seasonal_52 is enabled)
            active_baselines = [
                b for b in baselines
                if b != "baseline_seasonal_naive" or include_seasonal_52
            ]

            eval_by_h: dict[int, Any] = {}
            for h in horizons:
                X_h, y_h, meta_h = create_dataset_for_horizon(
                    df,
                    h=h,
                    target_col="admissions_count",
                    include_seasonal_lag52=include_seasonal_52,
                    include_pct_reporting=cfg["features"]["include_pct_reporting"],
                )
                eval_h = evaluate_horizon(
                    X_h,
                    y_h,
                    meta_h,
                    h=h,
                    baselines=active_baselines,
                    candidates=candidates,
                    interval_level=interval_level,
                    random_seed=random_seed,
                )
                eval_by_h[h] = {
                    "eval": eval_h,
                    "X": X_h,
                    "y": y_h,
                    "meta": meta_h,
                }

            # Reference split info from horizon 1
            splits_1 = eval_by_h[1]["eval"]["splits"]
            y_train_arr = eval_by_h[1]["y"].iloc[splits_1["train_idx"]].to_numpy()
            default_threshold = float(np.percentile(y_train_arr, threshold_pct))

            # Reference level: mean of last 4 observed weeks (F8)
            last_4_counts = df["admissions_count"].dropna().iloc[-4:].tolist()
            reference_level = float(np.mean(last_4_counts)) if last_4_counts else 0.0

            data_end_date = df["week_end_date"].iloc[-1]
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            config_json_data = {
                "config_hash": config_hash,
                "library_versions": {
                    "scikit-learn": sklearn.__version__,
                    "numpy": np.__version__,
                    "pandas": pd.__version__,
                    "carecast": getattr(carecast, "__version__", "0.1.0"),
                },
                "raw_file_sha256": raw_sha256,
                "code_version": git_commit,
                "clipping_notes": "All negative point and lower predictions clipped to 0.0",
                "training_start": start_date,
                "include_seasonal_lag52": include_seasonal_52,
            }

            # TRANSACTION START FOR THIS SERIES
            conn.execute("BEGIN TRANSACTION;")

            # 1. Update previous runs for this series
            conn.execute(
                """
                UPDATE model_runs
                SET is_current = 0
                WHERE jurisdiction_code = 'US' AND disease_code = ?;
                """,
                (disease,),
            )

            # 2. Insert T7 model_runs
            cur = conn.execute(
                """
                INSERT INTO model_runs
                    (created_at, jurisdiction_code, disease_code, source_id, target_kind,
                     data_end_date, train_start, train_end, valid_start, valid_end,
                     test_start, test_end, n_train, n_valid, n_test, interval_level,
                     default_threshold, default_threshold_method, reference_level,
                     random_seed, config_json, data_sha256, code_version, is_current)
                VALUES
                    (?, 'US', ?, ?, 'count', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
                """,
                (
                    now_iso,
                    disease,
                    source_id,
                    data_end_date,
                    splits_1["train_start"],
                    splits_1["train_end"],
                    splits_1["valid_start"],
                    splits_1["valid_end"],
                    splits_1["test_start"],
                    splits_1["test_end"],
                    splits_1["n_train"],
                    splits_1["n_valid"],
                    splits_1["n_test"],
                    interval_level,
                    default_threshold,
                    threshold_method,
                    reference_level,
                    random_seed,
                    json.dumps(config_json_data),
                    raw_sha256,
                    git_commit,
                ),
            )
            run_id = cur.lastrowid

            # 3. Insert T8 evaluation_metrics & T9 backtest_predictions
            for h in horizons:
                eval_data = eval_by_h[h]["eval"]
                for m_row in eval_data["metrics"]:
                    conn.execute(
                        """
                        INSERT INTO evaluation_metrics
                            (run_id, horizon_weeks, model_name, split, mae, rmse, n_eval,
                             mae_vs_persistence, is_selected, interval_coverage, beats_persistence)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            run_id,
                            m_row["horizon_weeks"],
                            m_row["model_name"],
                            m_row["split"],
                            m_row["mae"],
                            m_row["rmse"],
                            m_row["n_eval"],
                            m_row["mae_vs_persistence"],
                            m_row["is_selected"],
                            m_row["interval_coverage"],
                            m_row["beats_persistence"],
                        ),
                    )

                for m_name, splits_res in eval_data["backtest_results"].items():
                    for split_name, res_dict in splits_res.items():
                        for act, pred, m_meta in zip(
                            res_dict["actual"], res_dict["predicted"], res_dict["meta"]
                        ):
                            conn.execute(
                                """
                                INSERT INTO backtest_predictions
                                    (run_id, model_name, horizon_weeks, split,
                                     origin_week_end_date, target_week_end_date, actual, predicted)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                                """,
                                (
                                    run_id,
                                    m_name,
                                    h,
                                    split_name,
                                    m_meta["origin_week_end_date"],
                                    m_meta["target_week_end_date"],
                                    act,
                                    pred,
                                ),
                            )

            # 4. Generate & Insert T10 forecasts and T11 feature_contributions
            for h in horizons:
                eval_data = eval_by_h[h]["eval"]
                X_h = eval_by_h[h]["X"]
                y_h = eval_by_h[h]["y"]
                best_model_name = eval_data["selected_model"]

                # Refit selected model on full dataset through data_end_date
                final_model = get_model(best_model_name, random_state=random_seed)
                final_model.fit(X_h, y_h)

                # Feature vector at the latest observed date (origin = data_end_date)
                latest_origin_idx = len(df) - 1
                latest_features = build_feature_row(
                    df,
                    origin_idx=latest_origin_idx,
                    h=h,
                    target_col="admissions_count",
                    include_seasonal_lag52=include_seasonal_52,
                    include_pct_reporting=cfg["features"]["include_pct_reporting"],
                )
                if latest_features is None:
                    raise RuntimeError(f"Could not build forecast features at origin {data_end_date} for h={h}")

                X_forecast = pd.DataFrame([latest_features])
                point_pred = max(0.0, float(final_model.predict(X_forecast)[0]))
                lower_pred = min(point_pred, max(0.0, float(point_pred + eval_data["q_low"])))
                upper_pred = max(point_pred, float(point_pred + eval_data["q_high"]))

                target_date_iso = (
                    datetime.fromisoformat(data_end_date) + pd.Timedelta(weeks=h)
                ).strftime("%Y-%m-%d")

                conn.execute(
                    """
                    INSERT INTO forecasts
                        (run_id, horizon_weeks, origin_week_end_date, target_week_end_date,
                         model_name, point, lower, upper)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        run_id,
                        h,
                        data_end_date,
                        target_date_iso,
                        best_model_name,
                        point_pred,
                        lower_pred,
                        upper_pred,
                    ),
                )

                # T11 Feature contributions
                if best_model_name == "linear_lag" and isinstance(final_model, LinearLagModel):
                    base_val, contribs = compute_linear_contributions(final_model, latest_features)
                    conn.execute(
                        """
                        INSERT INTO feature_contributions
                            (run_id, horizon_weeks, method, feature_name, value, feature_value)
                        VALUES (?, ?, 'linear_contribution', '__base__', ?, NULL);
                        """,
                        (run_id, h, base_val),
                    )
                    for c in contribs:
                        conn.execute(
                            """
                            INSERT INTO feature_contributions
                                (run_id, horizon_weeks, method, feature_name, value, feature_value)
                            VALUES (?, ?, 'linear_contribution', ?, ?, ?);
                            """,
                            (run_id, h, c["feature_name"], c["value"], c["feature_value"]),
                        )

                # Permutation importance on the validation split
                v_idx = splits_1["valid_idx"]
                X_val = X_h.iloc[v_idx]
                y_val = y_h.iloc[v_idx]
                perm_imps = compute_permutation_importance(
                    final_model,
                    X_val,
                    y_val,
                    n_repeats=cfg["explain"]["permutation_repeats"],
                    random_seed=random_seed,
                )
                for pi in perm_imps:
                    conn.execute(
                        """
                        INSERT INTO feature_contributions
                            (run_id, horizon_weeks, method, feature_name, value, feature_value)
                        VALUES (?, ?, 'permutation_importance', ?, ?, NULL);
                        """,
                        (run_id, h, pi["feature_name"], pi["value"]),
                    )

            conn.commit()
            print(f"[OK] Series {disease.upper()} persisted successfully (run_id={run_id}).")
            results_summary[disease] = {
                "run_id": run_id,
                "data_end_date": data_end_date,
                "horizons": {
                    h: {
                        "selected_model": eval_by_h[h]["eval"]["selected_model"],
                        "beats_persistence": eval_by_h[h]["eval"]["beats_persistence"],
                        "test_coverage": eval_by_h[h]["eval"]["test_coverage"],
                    }
                    for h in horizons
                },
            }

        return results_summary
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def cmd_check(db_path: Path | str | None = None) -> int:
    """Print data quality and summary check report."""
    if db_path is None:
        db_path = get_settings().db_path
    db_file = Path(db_path)
    if not db_file.exists():
        print(f"[FAIL] Database file not found: {db_path}")
        return 1

    print(f"--> Checking database quality in {db_path}...")
    conn = connect_ro(db_path)
    try:
        # Summary of observations
        obs = conn.execute(
            """
            SELECT disease_code,
                   COUNT(*) as total_weeks,
                   MIN(week_end_date) as start_date,
                   MAX(week_end_date) as end_date,
                   MIN(admissions_count) as min_count,
                   MAX(admissions_count) as max_count,
                   AVG(admissions_count) as avg_count,
                   SUM(CASE WHEN admissions_count = 0 THEN 1 ELSE 0 END) as zero_counts,
                   SUM(CASE WHEN admissions_count IS NULL THEN 1 ELSE 0 END) as null_counts
            FROM weekly_observations
            WHERE jurisdiction_code = 'US'
            GROUP BY disease_code
            ORDER BY disease_code;
            """
        ).fetchall()

        print("\n================ Observation Summary (US) ================")
        print(f"{'Disease':<10} {'Weeks':<8} {'Start Date':<12} {'End Date':<12} {'Min':<8} {'Max':<8} {'Avg':<10} {'Zeros':<6}")
        print("-" * 76)
        for r in obs:
            avg_str = f"{r['avg_count']:.1f}" if r['avg_count'] is not None else "N/A"
            min_str = f"{r['min_count']:.0f}" if r['min_count'] is not None else "N/A"
            max_str = f"{r['max_count']:.0f}" if r['max_count'] is not None else "N/A"
            print(
                f"{r['disease_code']:<10} {r['total_weeks']:<8} {r['start_date']:<12} {r['end_date']:<12} "
                f"{min_str:<8} {max_str:<8} {avg_str:<10} {r['zero_counts']:<6}"
            )

        # Summary of quality issues
        issues = conn.execute(
            """
            SELECT check_name, severity, disease_code, COUNT(*) as count
            FROM data_quality_issues
            GROUP BY check_name, severity, disease_code
            ORDER BY severity DESC, check_name, disease_code;
            """
        ).fetchall()

        print("\n================ Data Quality Issues ================")
        if not issues:
            print("[OK] No data quality issues recorded.")
        else:
            print(f"{'Check Name':<25} {'Severity':<10} {'Disease':<10} {'Count':<6}")
            print("-" * 55)
            for qi in issues:
                d_str = qi["disease_code"] or "All"
                print(f"{qi['check_name']:<25} {qi['severity']:<10} {d_str:<10} {qi['count']:<6}")

        print("====================================================\n")
        return 0
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for carecast.pipeline."""
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description="CareCast Pipeline Orchestrator")
    parser.add_argument(
        "commands",
        nargs="+",
        help="One or more commands to execute in sequence: migrate, ingest, train, check, rebuild",
    )
    parser.add_argument("--csv", dest="csv_path", default=None, help="Path to raw CSV file for ingest")
    parser.add_argument("--db", dest="db_path", default=None, help="Path to SQLite database")
    parser.add_argument("--mapping", dest="mapping_path", default="config/dataset_mapping.toml", help="Path to mapping TOML")
    parser.add_argument("--config", dest="config_path", default="config/pipeline.toml", help="Path to pipeline TOML")

    args = parser.parse_args(argv)

    for cmd in args.commands:
        cmd_lower = cmd.lower()
        if cmd_lower == "migrate":
            cmd_migrate(db_path=args.db_path)
        elif cmd_lower == "ingest":
            cmd_ingest(csv_path=args.csv_path, db_path=args.db_path, mapping_path=args.mapping_path)
        elif cmd_lower == "train":
            cmd_train(db_path=args.db_path, config_path=args.config_path)
        elif cmd_lower == "check":
            cmd_check(db_path=args.db_path)
        elif cmd_lower == "rebuild":
            cmd_migrate(db_path=args.db_path)
            cmd_ingest(csv_path=args.csv_path, db_path=args.db_path, mapping_path=args.mapping_path)
            cmd_train(db_path=args.db_path, config_path=args.config_path)
        else:
            print(f"[FAIL] Unknown command: {cmd}. Supported: migrate, ingest, train, check, rebuild")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
