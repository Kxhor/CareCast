"""Verification script comparing filtered CSV row counts with database row counts."""

import csv
import sqlite3
from pathlib import Path


def main() -> None:
    csv_file = Path("data/raw/ua7e-t2fy.csv")
    db_file = Path("data/carecast.db")

    with csv_file.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        usa_rows = [r for r in reader if r["Geographic aggregation"].strip() == "USA"]

    csv_usa_count = len(usa_rows)

    csv_flu_count = sum(
        1 for r in usa_rows
        if r["Total Influenza Admissions"].strip() or r["Total number of Influenza Admissions per 100,000 population"].strip()
    )
    csv_covid_count = sum(
        1 for r in usa_rows
        if r["Total COVID-19 Admissions"].strip() or r["Total number of COVID-19 Admissions per 100,000 population"].strip()
    )
    csv_rsv_count = sum(
        1 for r in usa_rows
        if r["Total RSV Admissions"].strip() or r["Total number of RSV Admissions per 100,000 population"].strip()
    )

    conn = sqlite3.connect(db_file)
    db_total = conn.execute("SELECT COUNT(*) FROM weekly_observations;").fetchone()[0]
    db_flu = conn.execute("SELECT COUNT(*) FROM weekly_observations WHERE disease_code = 'flu';").fetchone()[0]
    db_covid = conn.execute("SELECT COUNT(*) FROM weekly_observations WHERE disease_code = 'covid19';").fetchone()[0]
    db_rsv = conn.execute("SELECT COUNT(*) FROM weekly_observations WHERE disease_code = 'rsv';").fetchone()[0]
    conn.close()

    print("=== Row Count Comparison (Filtered CSV vs DB) ===")
    print(f"Total USA rows in raw CSV: {csv_usa_count}")
    print(f"Flu observations:       Filtered CSV = {csv_flu_count} | Database = {db_flu} | Match = {csv_flu_count == db_flu}")
    print(f"COVID-19 observations:  Filtered CSV = {csv_covid_count} | Database = {db_covid} | Match = {csv_covid_count == db_covid}")
    print(f"RSV observations:       Filtered CSV = {csv_rsv_count} | Database = {db_rsv} | Match = {csv_rsv_count == db_rsv}")
    print(f"Total observations:     Filtered CSV = {csv_flu_count + csv_covid_count + csv_rsv_count} | Database = {db_total} | Match = {csv_flu_count + csv_covid_count + csv_rsv_count == db_total}")


if __name__ == "__main__":
    main()
