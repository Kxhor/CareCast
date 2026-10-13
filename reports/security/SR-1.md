# Incremental Security Review 1 (SR-1) — Phase 2

**Date / Time:** 13 Oct 2026  
**Scope:** Code modified/added since `phase-1-approved` (`carecast/ingest.py`, `carecast/pipeline.py`, `tests/unit/test_ingest.py`, `tests/unit/test_quality.py`, `tests/unit/test_sql_guard.py`, `tests/unit/test_schema_constraints.py`, `tests/fixtures/`)  
**Target:** Phase 2 Data Acquisition, Validation & Database  
**Review Type:** Incremental Review (Master Prompt #1 / TRD §9.3 INC-01...INC-10)

---

## 1. Security Checklist (INC-01 – INC-10)

| Control | Applicability & Rationale | Status | Findings | Fix / Mitigation | Evidence |
|---|---|---|---|---|---|
| **INC-01 Permission checks** | **NOT APPLICABLE**. Phase 2 consists exclusively of offline ETL CLI commands (`migrate`, `ingest`, `check`). No HTTP API, user accounts, or web endpoints exist at this phase. | **N/A** | None. No web routes or state-changing user endpoints. | N/A | `carecast/pipeline.py` is CLI offline only. |
| **INC-02 Secrets, API keys, tokens** | **APPLICABLE**. Repo files must contain zero embedded secrets or credentials. | **PASS** | None. `git grep` verified zero credentials or private tokens. | None required. | `git grep -nEi "(api[_-]?key\|secret\|token...)"` clean (only comments stating no secrets). |
| **INC-03 User input validation** | **APPLICABLE**. Ingestion reads external CSV files which must be strictly validated. | **PASS** | Dates verified for Saturday (`_is_saturday`), non-numeric and negative values coerced/logged, column names verified against mapping TOML. | Implemented in `carecast/ingest.py`. | Tested in `test_at_02_missing_column_aborts` and `test_at_03_defects_detected_and_logged`. |
| **INC-04 Safe error messages** | **APPLICABLE**. Ingestion error messages must provide actionable feedback without exposing sensitive internal internals. | **PASS** | `ValueError` raised on missing columns lists missing headers clearly. | Generic exceptions with descriptive text. | `test_at_02_missing_column_aborts` verifies error message. |
| **INC-05 UGC sanitisation** | **NOT APPLICABLE**. No user-generated content or user inputs are stored or rendered. Observations originate from public CDC government aggregates. | **N/A** | None. | N/A | Schema only accepts numerical aggregates and predefined disease codes. |
| **INC-06 Parameterised SQL** | **APPLICABLE**. All database queries must use `?` parameterised placeholders. | **PASS** | Zero f-strings, `%`, or `.format()` string concatenation found in SQL execution calls. | Static AST analysis guard in `test_sql_guard.py`. | `tests/unit/test_sql_guard.py::test_at_05_sql_guard_no_dynamic_queries` PASSED. |
| **INC-07 File uploads** | **NOT APPLICABLE**. No HTTP file upload endpoints exist. CLI ingest takes local file paths. | **N/A** | None. | N/A | No multipart or upload handlers exist. |
| **INC-08 Rate limiting** | **NOT APPLICABLE**. Phase 2 runs offline batch pipelines only; API layer is built in Phase 4. | **N/A** | None. | N/A | No HTTP endpoints in Phase 2. |
| **INC-09 CSRF** | **NOT APPLICABLE**. No web server or cookies exist in Phase 2. | **N/A** | None. | N/A | No cookies, sessions, or HTTP listeners. |
| **INC-10 Sensitive data exposure** | **APPLICABLE**. Verification that no patient-level identifying information (PII/PHI) exists in the database. | **PASS** | AT-45 verified zero patient-identifying columns (`patient_id`, `mrn`, `ssn`, `dob`, etc.). Only national/jurisdiction aggregates stored. | Strict schema definitions with CHECK constraints. | `tests/unit/test_schema_constraints.py::test_at_45_privacy_schema_check` PASSED. |

---

## 2. Automated Security Scans

### A. Bandit Security Linter
- **Command:** `python -m bandit -r carecast -q`
- **Output:** Clean exit (code 0), 0 issues identified.

### B. Secret Scan
- **Command:** `git grep -nEi "(api[_-]?key|secret|token|passwd|password|bearer|private[_-]?key)" -- . ":(exclude)docs" ":(exclude)reports"`
- **Output:** Clean — 0 secrets in application files.

---

## 3. What Was Changed and Why
- Added `seen_keys: set[tuple[str, str, str]]` in `carecast/ingest.py` to actively catch duplicate observations within a CSV and record `duplicate_key` warnings in `data_quality_issues`.
- Implemented `tests/unit/test_sql_guard.py` using Python AST static inspection to guarantee no SQL queries use f-strings or string concatenation.
- Implemented negative constraint tests in `tests/unit/test_schema_constraints.py` validating that SQLite CHECK constraints enforce Saturday dates, positive admission values, and disjoint train/valid/test blocks.

---

## 4. Residual Risks
- Raw CDC dataset is an external download; integrity is protected by recording and verifying file SHA-256 before ingest.
- No UI exists at this phase; screenshot evidence is not applicable.
