"""CLI pipeline orchestrator (Phase 2/3).

Supports:
- migrate: run DB schema migrations
- ingest: parse and validate CDC CSV dataset
- check: display data quality report from data_quality_issues
- rebuild: run migrate, then ingest
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

from carecast.db import connect_ro, run_migrations
from carecast.ingest import ingest_csv
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
        # Default to primary candidate if present in data/raw/
        raw_candidates = [
            Path("data/raw/ua7e-t2fy.csv"),
            Path("data/raw/Weekly_Hospital_Respiratory_Data__HRD__Metrics_by_Jurisdiction__National_Healthcare_Safety_Network__NHSN_.csv"),
        ]
        found = [p for p in raw_candidates if p.exists()]
        if not found:
            # Fall back to any csv in data/raw
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
        help="One or more commands to execute in sequence: migrate, ingest, check, rebuild",
    )
    parser.add_argument("--csv", dest="csv_path", default=None, help="Path to raw CSV file for ingest")
    parser.add_argument("--db", dest="db_path", default=None, help="Path to SQLite database")
    parser.add_argument("--mapping", dest="mapping_path", default="config/dataset_mapping.toml", help="Path to mapping TOML")

    args = parser.parse_args(argv)

    for cmd in args.commands:
        cmd_lower = cmd.lower()
        if cmd_lower == "migrate":
            cmd_migrate(db_path=args.db_path)
        elif cmd_lower == "ingest":
            cmd_ingest(csv_path=args.csv_path, db_path=args.db_path, mapping_path=args.mapping_path)
        elif cmd_lower == "check":
            cmd_check(db_path=args.db_path)
        elif cmd_lower == "rebuild":
            cmd_migrate(db_path=args.db_path)
            cmd_ingest(csv_path=args.csv_path, db_path=args.db_path, mapping_path=args.mapping_path)
        else:
            print(f"[FAIL] Unknown command: {cmd}. Supported: migrate, ingest, check, rebuild")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
