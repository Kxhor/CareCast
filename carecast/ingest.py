"""Data ingestion module: maps CDC CSV → SQLite (F1.1–F1.6).

Reads a CDC NHSN CSV using config/dataset_mapping.toml.
Never modifies the raw file. Records SHA-256 + row count in T2.
Idempotent: re-running adds 0 rows (UNIQUE constraint on T5).
Uses parameterised SQL only (no string-built SQL).
"""

from __future__ import annotations

import csv
import hashlib
import logging
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from carecast.db import connect_rw
from carecast.quality import run_quality_checks

logger = logging.getLogger(__name__)

# Canonical disease codes (must match T4 seed data).
_DISEASE_CODES: tuple[str, ...] = ("flu", "covid19", "rsv")

# Expected Saturday weekday index (strftime %w = 6).
_SATURDAY = 5  # Python date.weekday(): Monday=0, Saturday=5


def _sha256_file(path: Path) -> str:
    """Return hex SHA-256 of a file without loading it entirely into memory."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _count_rows(path: Path) -> int:
    """Count data rows in a CSV file (excluding the header)."""
    with path.open(newline="", encoding="utf-8") as f:
        return sum(1 for _ in f) - 1  # subtract header


def _parse_date(raw: str) -> str | None:
    """Parse a date string to ISO YYYY-MM-DD; return None if unparseable."""
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw[:len(fmt) + 3], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Try ISO prefix truncation
    if len(raw) >= 10:
        try:
            datetime.strptime(raw[:10], "%Y-%m-%d")
            return raw[:10]
        except ValueError:
            pass
    return None


def _is_saturday(date_str: str) -> bool:
    """Return True if the date string (YYYY-MM-DD) is a Saturday."""
    from datetime import date as date_cls
    d = date_cls.fromisoformat(date_str)
    return d.weekday() == _SATURDAY


def _to_real(raw: str) -> float | None:
    """Coerce a CSV cell to float; return None if blank or non-numeric."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        val = float(raw)
        return val
    except ValueError:
        return None


def load_mapping(mapping_path: Path | str = "config/dataset_mapping.toml") -> dict[str, Any]:
    """Load and return the dataset column-mapping TOML."""
    path = Path(mapping_path)
    if not path.exists():
        raise FileNotFoundError(f"Mapping file not found: {path}")
    with path.open("rb") as f:
        return tomllib.load(f)


def _ensure_jurisdictions(conn: Any, jurisdiction_code: str, name: str, level: str) -> None:
    """Insert a jurisdiction row if it doesn't exist yet."""
    conn.execute(
        "INSERT OR IGNORE INTO jurisdictions (code, name, level) VALUES (?, ?, ?);",
        (jurisdiction_code, name, level),
    )


def ingest_csv(
    csv_path: Path | str,
    db_path: Path | str = "data/carecast.db",
    mapping_path: Path | str = "config/dataset_mapping.toml",
) -> dict[str, Any]:
    """Ingest a CDC CSV file into the carecast database.

    Steps (F1.1–F1.6):
    1. Load mapping TOML; abort if required columns are absent.
    2. Compute SHA-256 and row count of the raw file (never modified).
    3. Skip if this (dataset_id, sha256) pair is already recorded in T2.
    4. Parse every row; coerce and validate fields; log issues to T6.
    5. Upsert weekly_observations via INSERT OR IGNORE (idempotent).
    6. Record provenance in dataset_sources (T2).

    Returns a summary dict with keys: source_id, rows_inserted,
    rows_skipped, quality_issues_logged.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    mapping = load_mapping(mapping_path)
    src_cfg = mapping["source"]
    col_cfg = mapping["columns"]

    date_col = col_cfg["date_column"]
    jur_col = src_cfg["jurisdiction"]["jurisdiction_column"]
    national_val = src_cfg["jurisdiction"]["national_value"]

    # Verify that required columns exist in the CSV header.
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
    headers_set = set(headers)

    required_cols = [date_col, jur_col]
    for disease in _DISEASE_CODES:
        d_cfg = col_cfg["diseases"][disease]
        count_col = d_cfg.get("count_column", "")
        rate_col = d_cfg.get("rate_column", "")
        if count_col:
            required_cols.append(count_col)
        if rate_col:
            required_cols.append(rate_col)

    missing = [c for c in required_cols if c not in headers_set]
    if missing:
        raise ValueError(
            f"Required columns absent from CSV — aborting ingest.\n"
            f"Missing: {missing}\n"
            f"Available columns: {sorted(headers_set)}"
        )

    # Compute SHA-256 and row count of the raw file.
    file_sha256 = _sha256_file(csv_path)
    row_count = _count_rows(csv_path)
    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn = connect_rw(db_path)
    try:
        # Check idempotency: skip if (dataset_id, sha256) already ingested.
        existing = conn.execute(
            "SELECT id FROM dataset_sources WHERE dataset_id = ? AND file_sha256 = ?;",
            (src_cfg["dataset_id"], file_sha256),
        ).fetchone()
        if existing:
            logger.info("Already ingested (dataset_id=%s, sha256=%s). Skipping.",
                        src_cfg["dataset_id"], file_sha256[:8])
            return {
                "source_id": existing["id"],
                "rows_inserted": 0,
                "rows_skipped": 0,
                "quality_issues_logged": 0,
                "already_ingested": True,
            }

        # Insert dataset source record (T2).
        cur = conn.execute(
            """
            INSERT INTO dataset_sources
                (name, publisher, dataset_id, url, licence_note,
                 retrieved_at, file_name, file_sha256, row_count, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                src_cfg["name"],
                src_cfg["publisher"],
                src_cfg["dataset_id"],
                src_cfg["url"],
                src_cfg.get("licence_note"),
                retrieved_at,
                csv_path.name,
                file_sha256,
                row_count,
                None,
            ),
        )
        source_id: int = cur.lastrowid  # type: ignore[assignment]
        conn.commit()

        # Ensure national jurisdiction exists in T3.
        _ensure_jurisdictions(conn, "US", "United States (national)", "national")
        conn.commit()

        # Parse and validate rows.
        rows_inserted = 0
        rows_skipped = 0
        quality_rows: list[dict[str, Any]] = []

        with csv_path.open(newline="", encoding="utf-8") as f:
            reader_dict = csv.DictReader(f)
            for lineno, row in enumerate(reader_dict, start=2):  # 2 = first data row
                raw_jur = row[jur_col].strip()
                # Only ingest the national (USA) row.
                if raw_jur != national_val:
                    rows_skipped += 1
                    continue

                # Parse and validate date.
                raw_date = row[date_col].strip()
                date_str = _parse_date(raw_date)
                if date_str is None:
                    quality_rows.append({
                        "check_name": "non_numeric",
                        "severity": "error",
                        "detail": f"Line {lineno}: unparseable date '{raw_date}'",
                        "week_start": None,
                        "week_end": None,
                        "jurisdiction_code": None,
                        "disease_code": None,
                    })
                    rows_skipped += 1
                    continue

                if not _is_saturday(date_str):
                    quality_rows.append({
                        "check_name": "non_saturday",
                        "severity": "error",
                        "detail": f"Line {lineno}: date {date_str} is not a Saturday",
                        "week_start": None,
                        "week_end": date_str,
                        "jurisdiction_code": "US",
                        "disease_code": None,
                    })
                    rows_skipped += 1
                    continue

                # Parse each disease.
                for disease in _DISEASE_CODES:
                    d_cfg = col_cfg["diseases"][disease]
                    count_col = d_cfg.get("count_column", "")
                    rate_col = d_cfg.get("rate_column", "")
                    level_col = d_cfg.get("level_column", "")
                    hosp_col = d_cfg.get("reporting_hospitals_column", "")
                    pct_col = d_cfg.get("pct_reporting_column", "")

                    adm_count: float | None = None
                    adm_rate: float | None = None

                    if count_col:
                        raw_count = row.get(count_col, "").strip()
                        adm_count = _to_real(raw_count)
                        if raw_count and adm_count is None:
                            quality_rows.append({
                                "check_name": "non_numeric",
                                "severity": "warning",
                                "detail": f"Line {lineno}: {disease} count non-numeric '{raw_count}'",
                                "week_start": None,
                                "week_end": date_str,
                                "jurisdiction_code": "US",
                                "disease_code": disease,
                            })
                        elif adm_count is not None and adm_count < 0:
                            quality_rows.append({
                                "check_name": "negative_value",
                                "severity": "error",
                                "detail": f"Line {lineno}: {disease} count negative {adm_count}",
                                "week_start": None,
                                "week_end": date_str,
                                "jurisdiction_code": "US",
                                "disease_code": disease,
                            })
                            adm_count = None

                    if rate_col:
                        raw_rate = row.get(rate_col, "").strip()
                        adm_rate = _to_real(raw_rate)
                        if raw_rate and adm_rate is None:
                            quality_rows.append({
                                "check_name": "non_numeric",
                                "severity": "warning",
                                "detail": f"Line {lineno}: {disease} rate non-numeric '{raw_rate}'",
                                "week_start": None,
                                "week_end": date_str,
                                "jurisdiction_code": "US",
                                "disease_code": disease,
                            })
                        elif adm_rate is not None and adm_rate < 0:
                            quality_rows.append({
                                "check_name": "negative_value",
                                "severity": "error",
                                "detail": f"Line {lineno}: {disease} rate negative {adm_rate}",
                                "week_start": None,
                                "week_end": date_str,
                                "jurisdiction_code": "US",
                                "disease_code": disease,
                            })
                            adm_rate = None

                    # Must have at least one of count or rate (per T5 CHECK).
                    if adm_count is None and adm_rate is None:
                        # For RSV this is expected for early rows — log as info.
                        sev = "info" if disease == "rsv" else "warning"
                        quality_rows.append({
                            "check_name": "missing_week",
                            "severity": sev,
                            "detail": f"Line {lineno}: {disease} has neither count nor rate for {date_str}",
                            "week_start": None,
                            "week_end": date_str,
                            "jurisdiction_code": "US",
                            "disease_code": disease,
                        })
                        continue

                    # Parse optional fields.
                    admission_level: str | None = None
                    if level_col:
                        admission_level = row.get(level_col, "").strip() or None

                    reporting_hospitals: float | None = None
                    if hosp_col:
                        reporting_hospitals = _to_real(row.get(hosp_col, ""))

                    pct_reporting: float | None = None
                    if pct_col:
                        raw_pct = row.get(pct_col, "").strip()
                        pct_reporting = _to_real(raw_pct)
                        if pct_reporting is not None and not (0 <= pct_reporting <= 100):
                            quality_rows.append({
                                "check_name": "coverage_out_of_range",
                                "severity": "warning",
                                "detail": f"Line {lineno}: {disease} pct_reporting {pct_reporting} outside [0,100]",
                                "week_start": None,
                                "week_end": date_str,
                                "jurisdiction_code": "US",
                                "disease_code": disease,
                            })
                            pct_reporting = None

                    # Upsert into T5 (INSERT OR IGNORE → idempotent).
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO weekly_observations
                            (source_id, jurisdiction_code, disease_code,
                             week_end_date, admissions_count, admissions_rate_per_100k,
                             admission_level, reporting_hospitals, pct_reporting, is_imputed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0);
                        """,
                        (
                            source_id,
                            "US",
                            disease,
                            date_str,
                            adm_count,
                            adm_rate,
                            admission_level,
                            int(reporting_hospitals) if reporting_hospitals is not None else None,
                            pct_reporting,
                        ),
                    )
                    if conn.execute("SELECT changes();").fetchone()[0] > 0:
                        rows_inserted += 1

        conn.commit()

        # Write quality issues to T6 in one batch.
        for q in quality_rows:
            conn.execute(
                """
                INSERT INTO data_quality_issues
                    (source_id, jurisdiction_code, disease_code,
                     check_name, severity, detail, week_start, week_end)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    source_id,
                    q["jurisdiction_code"],
                    q["disease_code"],
                    q["check_name"],
                    q["severity"],
                    q["detail"],
                    q["week_start"],
                    q["week_end"],
                ),
            )
        conn.commit()

        # Run structural quality checks (gap analysis, etc.).
        extra_issues = run_quality_checks(conn, source_id)
        for qi in extra_issues:
            conn.execute(
                """
                INSERT INTO data_quality_issues
                    (source_id, jurisdiction_code, disease_code,
                     check_name, severity, detail, week_start, week_end)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    source_id,
                    qi["jurisdiction_code"],
                    qi["disease_code"],
                    qi["check_name"],
                    qi["severity"],
                    qi["detail"],
                    qi.get("week_start"),
                    qi.get("week_end"),
                ),
            )
        conn.commit()

        total_quality = len(quality_rows) + len(extra_issues)
        logger.info(
            "Ingest complete: source_id=%d, inserted=%d, skipped=%d, quality_issues=%d",
            source_id, rows_inserted, rows_skipped, total_quality,
        )
        return {
            "source_id": source_id,
            "rows_inserted": rows_inserted,
            "rows_skipped": rows_skipped,
            "quality_issues_logged": total_quality,
            "already_ingested": False,
        }
    finally:
        conn.close()
