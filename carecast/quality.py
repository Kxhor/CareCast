"""Data quality checks for ingested weekly observations.

Performs post-ingest structural checks: missing weeks, long gaps,
duplicate detection, etc. Returns a list of issue dicts for T6.
These checks are run after the per-row validation in ingest.py.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any


def _iter_weeks(start: str, end: str):
    """Yield successive Saturday dates (YYYY-MM-DD) from start to end (inclusive)."""
    d = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    while d <= end_d:
        yield d.isoformat()
        d += timedelta(weeks=1)


def run_quality_checks(
    conn: sqlite3.Connection,
    source_id: int,
    jurisdiction_code: str = "US",
    max_gap_weeks: int = 2,
) -> list[dict[str, Any]]:
    """Run structural quality checks on the ingested observations.

    Checks performed:
    - missing_week: expected Saturday dates with no row in T5.
    - long_gap: contiguous missing run > max_gap_weeks.
    - duplicate_key: (jurisdiction, disease, week_end_date) duplicates in T5.

    Returns list of issue dicts compatible with T6 insert in ingest.py.
    """
    issues: list[dict[str, Any]] = []

    # Fetch all loaded dates per disease for this source.
    rows = conn.execute(
        """
        SELECT disease_code, week_end_date
        FROM weekly_observations
        WHERE source_id = ? AND jurisdiction_code = ?
        ORDER BY disease_code, week_end_date;
        """,
        (source_id, jurisdiction_code),
    ).fetchall()

    # Group by disease.
    from collections import defaultdict
    by_disease: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        by_disease[r["disease_code"]].append(r["week_end_date"])

    for disease, dates in by_disease.items():
        if not dates:
            continue

        # Check for duplicate dates (safety net — UNIQUE constraint should catch).
        seen: set[str] = set()
        for d in dates:
            if d in seen:
                issues.append({
                    "check_name": "duplicate_key",
                    "severity": "error",
                    "detail": f"{disease}: duplicate week_end_date {d}",
                    "week_start": None,
                    "week_end": d,
                    "jurisdiction_code": jurisdiction_code,
                    "disease_code": disease,
                })
            seen.add(d)

        # Check for missing weeks between first and last date.
        first, last = dates[0], dates[-1]
        dates_set = set(dates)
        gap_start: str | None = None
        gap_len = 0

        for expected in _iter_weeks(first, last):
            if expected not in dates_set:
                if gap_start is None:
                    gap_start = expected
                gap_len += 1
            else:
                if gap_start is not None:
                    # Report individual missing weeks as info.
                    issues.append({
                        "check_name": "missing_week",
                        "severity": "info",
                        "detail": f"{disease}: {gap_len} missing week(s) from {gap_start}",
                        "week_start": gap_start,
                        "week_end": expected,
                        "jurisdiction_code": jurisdiction_code,
                        "disease_code": disease,
                    })
                    # Flag long gaps as warnings.
                    if gap_len > max_gap_weeks:
                        issues.append({
                            "check_name": "long_gap",
                            "severity": "warning",
                            "detail": (
                                f"{disease}: gap of {gap_len} week(s) exceeds "
                                f"imputation threshold ({max_gap_weeks}). "
                                f"Series may be unreliable from {gap_start}."
                            ),
                            "week_start": gap_start,
                            "week_end": expected,
                            "jurisdiction_code": jurisdiction_code,
                            "disease_code": disease,
                        })
                    gap_start = None
                    gap_len = 0

        # Handle trailing gap.
        if gap_start is not None:
            issues.append({
                "check_name": "missing_week",
                "severity": "info",
                "detail": f"{disease}: {gap_len} missing week(s) from {gap_start} to {last}",
                "week_start": gap_start,
                "week_end": last,
                "jurisdiction_code": jurisdiction_code,
                "disease_code": disease,
            })
            if gap_len > max_gap_weeks:
                issues.append({
                    "check_name": "long_gap",
                    "severity": "warning",
                    "detail": (
                        f"{disease}: trailing gap of {gap_len} week(s) from {gap_start}."
                    ),
                    "week_start": gap_start,
                    "week_end": last,
                    "jurisdiction_code": jurisdiction_code,
                    "disease_code": disease,
                })

    return issues
