# Phase 2 Report — Data Acquisition, Validation & Database

**Date / Time:** 13 Oct 2026, 21:46–22:05 IST  
**Commit(s):** Initial tag `phase-1-approved`  
**Skills Applied:** `domain-modeling`, `codebase-design`, `test-driven-development`, `systematic-debugging`, `Ponytail`, `Security Review (incremental)`, `verification-before-completion`

---

## 1. Repo State Found at Start
- **Git Status:** Working tree clean at tag `phase-1-approved`.
- **Files Present:** Core framework modules (`carecast/settings.py`, `carecast/db.py`), migrations (`0001_core_data.sql`, `0002_forecasting.sql`), mapping configuration (`config/dataset_mapping.toml`), specification documents (`docs/`), and unit tests for settings, DB, and schema.

---

## 2. Docs Read
- `docs/PRD.md` (§2.4–2.5, §11, §12)
- `docs/BACKEND_SCHEMA.md` (all tables, views, and integrity constraints)
- `docs/TRD.md` (§5.1, §9.3, §12)
- `docs/IMPLEMENTATION_PLAN.md` (Phase 2 deliverables and gate checklist)
- `docs/ANTIGRAVITY_PROMPTS.md` (P-2 prompt and SR review prompt)

---

## 3. What Was Built (Files Created / Changed)
- **Data Acquisition:**
  - Acquired CDC NHSN CSV datasets via Socrata API into `data/raw/`:
    - `data/raw/ua7e-t2fy.csv` (Primary candidate: 24,578,284 bytes, 21,574 rows, 322 columns)
    - `data/raw/vdzy-6i9v.csv` (Secondary candidate: 124,492 bytes, 1,425 rows, 17 columns)
- **Synthetic Test Fixtures (TEST-ONLY):**
  - `tests/fixtures/README.md`: Explaining synthetic test nature.
  - `tests/fixtures/sample_valid.csv`: Deterministic valid CSV with quoted headers and Saturday dates.
  - `tests/fixtures/sample_missing_col.csv`: CSV missing required columns for AT-02 abort verification.
  - `tests/fixtures/sample_defects.csv`: CSV with injected duplicates, non-Saturday dates, negative counts, non-numeric cells, out-of-range coverage, and multi-week gaps.
- **Ingestion & Quality Engine:**
  - `carecast/ingest.py`: Enhanced with `seen_keys` tracking to record `duplicate_key` quality issues.
  - `carecast/quality.py`: Post-ingest structural gap analysis and data quality checking.
  - `carecast/pipeline.py`: CLI commands `migrate`, `ingest`, `check`, and `rebuild`.
- **Unit & Security Tests:**
  - `tests/unit/test_ingest.py`: AT-01 (idempotency), AT-02 (missing column abort), AT-03 (defect detection), AT-04 (SHA-256 integrity).
  - `tests/unit/test_quality.py`: Structural gap and long gap quality checks.
  - `tests/unit/test_sql_guard.py`: AT-05 static AST scan ensuring 100% parameterised SQL.
  - `tests/unit/test_schema_constraints.py`: AT-45 (privacy check: no patient identifiers) and negative SQLite CHECK constraint tests.
- **EDA & Verification Scripts:**
  - `scripts/compare_counts.py`: Compares filtered CSV row counts with SQLite observations.
  - `scripts/eda.py`: Comprehensive statistical analysis, seasonality profiling, regime break audit, and candidate training start evaluation.
  - `reports/eda_summary.md`: Detailed markdown summary of EDA findings.
- **Security Review:**
  - `reports/security/SR-1.md`: Incremental security review (INC-01 through INC-10).

---

## 4. Data Decision Record (OD-03 & OD-06 Evidence)

### 4.1 Headers and Metrics Verified from Real CSV
Inspection of the real header row in `data/raw/ua7e-t2fy.csv` verified 322 columns matching `config/dataset_mapping.toml`:
- **Date Column:** `Week Ending Date` (Format: ISO `YYYY-MM-DD`, always Saturdays).
- **Geographic Aggregation:** `Geographic aggregation` (National value = `USA`, 322 contiguous weeks).
- **Weekly New Admissions Count:**
  - Influenza: `Total Influenza Admissions` (Range: 0 – 55,544, Mean: 4,613.8)
  - COVID-19: `Total COVID-19 Admissions` (Range: 883 – 155,896, Mean: 25,459.9)
  - RSV: `Total RSV Admissions` (Range: 0 – 15,924, Mean: 2,104.2)
- **Weekly New Admission Rates:**
  - `"Total number of Influenza Admissions per 100,000 population"`
  - `"Total number of COVID-19 Admissions per 100,000 population"`
  - `"Total number of RSV Admissions per 100,000 population"`
- **Hospital Reporting Coverage:**
  - Reporting hospital counts and percentage reporting columns exist for all three diseases (`Number Hospitals Reporting...`, `Percent Hospitals Reporting...`).
- **Licence / Terms:** Public domain U.S. Government data (CDC NHSN). Free for use with attribution.
- **Date Range:** `2020-08-08` to `2026-10-03` (322 contiguous Saturday weeks).

### 4.2 Target Decision (OD-03)
- **Weekly new-admission COUNT exists directly in DS-2 (`ua7e-t2fy.csv`)** for all three respiratory diseases.
- Per PRD §2.5 decision rule: Target = **weekly new-admission count** (`admissions_count`).

### 4.3 Training Start Analysis & Trade-offs (OD-06)
1. **Option A (2020-08-08, 322 weeks):**
   - *Pros:* Maximum length of history.
   - *Cons:* Early flu reporting has 10 artificial zero weeks (2020-08-08 to 2020-10-10) during initial voluntary setup; extreme COVID-19 lockdown distortions.
2. **Option B (2021-10-02, 262 weeks, ~5.0 seasons):**
   - *Pros:* Discards voluntary onboarding zeros; captures regular seasonal winter spikes.
   - *Cons:* Winter 2021-2022 Omicron surge exhibits unprecedented peak amplitude.
3. **Option C (2022-10-01, 210 weeks, ~4.0 seasons) [Recommended for Flu & COVID-19]:**
   - *Pros:* Post-Omicron endemic stability; consistent hospital reporting compliance; representative seasonal waves.
   - *Cons:* Slightly shorter series (210 weeks).
4. **Option D (2023-10-07, 157 weeks, ~3.0 seasons) [Recommended for RSV]:**
   - *Pros:* **Synchronous baseline across all three diseases**; RSV reporting started on this date in DS-2 (zero missing weeks).

### 4.4 Disease Qualification Verdict
- **Influenza (`flu`)**: **QUALIFIES**. 322 contiguous weeks, high seasonal periodicity.
- **COVID-19 (`covid19`)**: **QUALIFIES**. 322 contiguous weeks, dual-wave seasonality.
- **RSV (`rsv`)**: **QUALIFIES (from 2023-10-07 onwards)**. 157 contiguous weeks, clean winter surge.

---

## 5. Validation Commands & Real Outputs

All validation commands were run and outputs recorded in `reports/logs/`:

### A. Full Pytest Suite (Unit, Ingest, Quality, Constraints, SQL Guard)
- **Command:** `python -m pytest -v`
- **Output Excerpt:**
  ```text
  tests/unit/test_db.py::test_connect_rw_creates_and_writes PASSED         [  3%]
  tests/unit/test_db.py::test_connect_ro_enforces_read_only PASSED         [  7%]
  tests/unit/test_db.py::test_connect_ro_missing_file_raises PASSED        [ 11%]
  tests/unit/test_db.py::test_migration_runner_skeleton PASSED             [ 15%]
  tests/unit/test_ingest.py::test_at_01_ingest_idempotency PASSED          [ 19%]
  tests/unit/test_ingest.py::test_at_02_missing_column_aborts PASSED       [ 23%]
  tests/unit/test_ingest.py::test_at_03_defects_detected_and_logged PASSED [ 26%]
  tests/unit/test_ingest.py::test_at_04_raw_file_sha256_recorded PASSED    [ 30%]
  tests/unit/test_quality.py::test_quality_checks_gap_detection PASSED     [ 34%]
  tests/unit/test_schema.py::test_migrations_fresh_db PASSED               [ 38%]
  tests/unit/test_schema.py::test_migrations_idempotency PASSED            [ 42%]
  tests/unit/test_schema_constraints.py::test_at_45_privacy_schema_check PASSED [ 46%]
  tests/unit/test_schema_constraints.py::test_negative_constraint_non_saturday_date PASSED [ 50%]
  tests/unit/test_schema_constraints.py::test_negative_constraint_negative_admissions PASSED [ 53%]
  tests/unit/test_schema_constraints.py::test_negative_constraint_train_valid_test_overlap PASSED [ 57%]
  tests/unit/test_settings.py::test_default_settings PASSED                [ 61%]
  tests/unit/test_settings.py::test_custom_settings_via_env PASSED         [ 65%]
  tests/unit/test_settings.py::test_docs_disabled_in_prod PASSED           [ 69%]
  tests/unit/test_settings.py::test_reject_invalid_env PASSED              [ 73%]
  tests/unit/test_settings.py::test_reject_invalid_rate_limit PASSED       [ 76%]
  tests/unit/test_settings.py::test_reject_invalid_log_level PASSED        [ 80%]
  tests/unit/test_settings.py::test_reject_db_path_inside_web PASSED       [ 84%]
  tests/unit/test_settings.py::test_load_toml_missing_file PASSED          [ 88%]
  tests/unit/test_smoke.py::test_import_carecast PASSED                    [ 92%]
  tests/unit/test_smoke.py::test_import_submodules PASSED                  [ 96%]
  tests/unit/test_sql_guard.py::test_at_05_sql_guard_no_dynamic_queries PASSED [100%]
  ============================= 26 passed in 1.04s ==============================
  ```
- **Result:** PASS ([reports/logs/p2-pytest.txt](reports/logs/p2-pytest.txt))

### B. Pipeline Migrate, Ingest & Check Execution
- **Command:** `python -m carecast.pipeline migrate ingest check`
- **Output Excerpt:**
  ```text
  --> Running migrations on data\carecast.db from migrations...
  [OK] Applied migrations: 0001_core_data, 0002_forecasting
  --> Ingesting data\raw\ua7e-t2fy.csv into data\carecast.db...
  [OK] Ingestion complete: source_id=1, inserted=801, skipped=21252, quality_issues=165
  --> Checking database quality in data\carecast.db...

  ================ Observation Summary (US) ================
  Disease    Weeks    Start Date   End Date     Min      Max      Avg        Zeros 
  ----------------------------------------------------------------------------
  covid19    322      2020-08-08   2026-10-03   883      155896   25459.9    0     
  flu        322      2020-08-08   2026-10-03   0        55544    4613.8     10    
  rsv        157      2023-10-07   2026-10-03   0        15924    2104.2     8     

  ================ Data Quality Issues ================
  Check Name                Severity   Disease    Count 
  -------------------------------------------------------
  missing_week              info       rsv        165   
  ====================================================
  ```
- **Result:** PASS ([reports/logs/p2-pipeline.txt](reports/logs/p2-pipeline.txt))

### C. Second Ingest Idempotency
- **Command:** `python -m carecast.pipeline ingest`
- **Output:**
  ```text
  --> Ingesting data\raw\ua7e-t2fy.csv into data\carecast.db...
  [OK] Already ingested (source_id=1). Added 0 rows.
  ```
- **Result:** PASS ([reports/logs/p2-idempotency.txt](reports/logs/p2-idempotency.txt))

### D. Filtered CSV vs Database Row Count Comparison
- **Command:** `python scripts/compare_counts.py`
- **Output:**
  ```text
  === Row Count Comparison (Filtered CSV vs DB) ===
  Total USA rows in raw CSV: 322
  Flu observations:       Filtered CSV = 322 | Database = 322 | Match = True
  COVID-19 observations:  Filtered CSV = 322 | Database = 322 | Match = True
  RSV observations:       Filtered CSV = 157 | Database = 157 | Match = True
  Total observations:     Filtered CSV = 801 | Database = 801 | Match = True
  ```
- **Result:** PASS ([reports/logs/p2-row-counts.txt](reports/logs/p2-row-counts.txt))

---

## 6. Acceptance Criteria Table (Phase 2)

| AT | Feature | Requirement / Pass Condition | Result | Evidence |
|---|---|---|---|---|
| **AT-01** | F1 | Ingest idempotency: running twice yields identical row counts (2nd inserts 0). | **PASS** | [`test_at_01_ingest_idempotency`](tests/unit/test_ingest.py) and [`reports/logs/p2-idempotency.txt`](reports/logs/p2-idempotency.txt). |
| **AT-02** | F1 | Missing/renamed required column aborts with an error and clear message. | **PASS** | [`test_at_02_missing_column_aborts`](tests/unit/test_ingest.py) passes. |
| **AT-03** | F1 | Defect fixture detects duplicate, non-Saturday, negative, non-numeric, gap. | **PASS** | [`test_at_03_defects_detected_and_logged`](tests/unit/test_ingest.py) verifies all logged in T6. |
| **AT-04** | F1 | Raw file SHA-256 recorded in T2; file remains unmodified after ingestion. | **PASS** | [`test_at_04_raw_file_sha256_recorded`](tests/unit/test_ingest.py) verifies recorded SHA matches. |
| **AT-05** | F1/N1 | Static scan: zero SQL queries built via f-string, concatenation, `%`, or `.format()`. | **PASS** | [`test_at_05_sql_guard_no_dynamic_queries`](tests/unit/test_sql_guard.py) AST scan passes clean. |
| **AT-45** | N6 | Schema privacy: zero patient-identifying fields (`patient_id`, `mrn`, `ssn`, `dob`). | **PASS** | [`test_at_45_privacy_schema_check`](tests/unit/test_schema_constraints.py) passes. |

---

## 7. Failures Encountered, Root Cause, Fix, Re-Validation

1. **Synthetic Fixture CSV Header Quoting:**
   - *Failure:* Initial `pytest` failed with `ValueError: Required columns absent from CSV` on `Total number of Influenza Admissions per 100,000 population`.
   - *Root Cause:* Header column name contained a comma (`100,000`), which caused CSV unquoted parsing to split into two columns.
   - *Fix:* Enclosed column headers containing commas in double quotes (`"Total number of ..."`).
   - *Re-validation:* Pytest passed cleanly with all 26 tests passing.
2. **Settings DB Path Attribute Name:**
   - *Failure:* Initial `python -m carecast.pipeline migrate` raised `AttributeError: 'Settings' object has no attribute 'carecast_db_path'`.
   - *Root Cause:* In `carecast/settings.py`, the property name is `db_path`.
   - *Fix:* Updated `carecast/pipeline.py` to use `get_settings().db_path`.
   - *Re-validation:* Pipeline execution completed successfully.
3. **Windows Console Unicode Output in EDA:**
   - *Failure:* Python script `scripts/eda.py` failed with `UnicodeEncodeError: 'charmap' codec can't encode character '\u2705'`.
   - *Root Cause:* Windows powershell default encoding is `cp1252`.
   - *Fix:* Reconfigured `sys.stdout` to UTF-8 and sanitized console output strings.
   - *Re-validation:* Re-ran `scripts/eda.py`; executed and output saved cleanly.

---

## 8. Deviations / Approvals Requested
- **Zero deviations from approved specification.**
- **Zero new dependencies added.** All dependencies conform strictly to TRD §3.2.

---

## 9. Security Review Summary
Incremental Security Review **SR-1** conducted and documented in [`reports/security/SR-1.md`](reports/security/SR-1.md).
- Automated Bandit scan: 0 issues.
- Secret scan: 0 secrets.
- AST SQL Guard: 0 string-built SQL calls.
- Privacy audit (AT-45): 0 patient identifiers.

---

## 10. Open Decisions for Approval Gate
- **OD-03 (Target Kind):** Recommend **`count`** (`admissions_count`), as weekly new admission counts exist cleanly in DS-2 for Flu, COVID-19, and RSV.
- **OD-06 (Training Start):**
  - For **Flu & COVID-19**: Recommend **`2022-10-01`** (4 full seasons, post-Omicron endemic period, consistent reporting). Alternative: `2021-10-02` (5 full seasons).
  - For **RSV**: Must be **`2023-10-07`** (inception date of RSV reporting in NHSN; 157 contiguous weeks).

---

## 11. Screenshots
N/A (No frontend UI in Phase 2).

---

## 12. Filled Gate Checklist (`IMPLEMENTATION_PLAN.md §6`)

```text
[x] Docs read and listed          [x] Repo state reported before changes
[x] Only this phase's scope built [x] No new dependency (or approval requested)
[x] Every AT for this phase run   [x] Raw outputs saved in reports/logs/
[x] Failures documented + fixed   [x] Security review done (SR-n) or N/A stated
[x] No fabricated numbers         [x] Deviations listed
[x] STOPPED and waiting for "APPROVED: PHASE 2"
```

---

**STOP — Awaiting exact reply:**  
`APPROVED: PHASE 2`  
Decisions: OD-03 target = `<count | rate>`, diseases = `<flu, covid19, rsv — or subset>`; OD-06 training_start = `<YYYY-MM-DD>`.
