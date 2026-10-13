# Incremental Security Review 2 (SR-2) — Phase 3

**Date / Time:** 13 Oct 2026  
**Scope:** Code modified/added since `phase-2-approved` (`carecast/features.py`, `carecast/models.py`, `carecast/evaluate.py`, `carecast/explain.py`, `carecast/pipeline.py`, `config/pipeline.toml`, `tests/unit/test_features.py`, `tests/unit/test_models.py`, `tests/unit/test_evaluate.py`, `tests/unit/test_explain.py`, `tests/unit/test_storage.py`)  
**Target:** Phase 3 Forecast Engine, Walk-Forward Evaluation & Explainability  
**Review Type:** Incremental Review (Master Prompt #1 / TRD §9.3 INC-01...INC-10)

---

## 1. Security Checklist (INC-01 – INC-10)

| Control | Applicability & Rationale | Status | Findings | Fix / Mitigation | Evidence |
|---|---|---|---|---|---|
| **INC-01 Permission checks** | **NOT APPLICABLE**. Phase 3 consists exclusively of offline forecasting and evaluation pipeline routines (`features.py`, `models.py`, `evaluate.py`, `explain.py`, `pipeline.py train`). No HTTP endpoints, user accounts, or web routes exist at this phase. | **N/A** | None. No HTTP server or user-facing endpoints. | N/A | Offline ML engine only. |
| **INC-02 Secrets, API keys, tokens** | **APPLICABLE**. Phase 3 files, model definitions, and configs must contain zero embedded credentials, API tokens, or secrets. | **PASS** | None. Secret scan returned clean. | None required. | `git grep -nEi "(api[_-]?key\|secret\|token...)"` clean. |
| **INC-03 User input validation** | **APPLICABLE**. Model training arguments, feature extraction indices, and configurations must be strictly bounded. | **PASS** | `config/pipeline.toml` parsed with `tomllib`. Horizon bounds checked between 1 and 4 in schema. Negative predictions clipped to 0.0 (`np.clip(..., 0.0, None)`). | Bounds enforced in code and database schema constraints. | `test_models.py::test_linear_lag_negative_clipping` PASSED. |
| **INC-04 Safe error messages** | **APPLICABLE**. Exception handling in model factories and pipeline execution must provide descriptive errors without leaking sensitive stack information. | **PASS** | `get_model` raises descriptive `ValueError` on unknown model architecture. Database rollback executed safely in `finally:` block. | Handled via structured exception handlers. | `test_models.py::test_get_model_factory` PASSED. |
| **INC-05 UGC sanitisation** | **NOT APPLICABLE**. CareCast processes no user-generated content. All observations originate from CDC public health aggregates. | **N/A** | None. | N/A | Model features and forecasts are strictly numerical aggregates. |
| **INC-06 Parameterised SQL** | **APPLICABLE**. All database insertions for T7–T11 must use `?` parameterised placeholders. | **PASS** | 100% of SQL queries in `cmd_train` and `pipeline.py` use `?` parameterised tuples. | AST-based static analysis guard enforces zero string formatting in SQL. | `test_sql_guard.py::test_at_05_sql_guard_no_dynamic_queries` PASSED. |
| **INC-07 File uploads** | **NOT APPLICABLE**. No file upload handlers or multipart routes exist in Phase 3. | **N/A** | None. | N/A | Offline CLI operation only. |
| **INC-08 Rate limiting** | **NOT APPLICABLE**. Rate limiting applies to HTTP API endpoints (Phase 4). Phase 3 is an offline batch execution command. | **N/A** | None. | N/A | No web listener or API routes. |
| **INC-09 CSRF** | **NOT APPLICABLE**. No web sessions, cookies, or browser clients exist in Phase 3. | **N/A** | None. | N/A | Stateless offline engine. |
| **INC-10 Sensitive data exposure** | **APPLICABLE**. Database storage must contain zero patient-level or identifying health information (HIPAA). | **PASS** | T7–T11 store only aggregate counts, evaluation metrics (MAE, RMSE), quantiles, and feature contributions. Zero patient identifiers. | Schema design audited via AT-45. | `test_schema_constraints.py::test_at_45_privacy_schema_check` PASSED. |

---

## 2. Automated Security Scans

### A. Bandit Security Linter
- **Command:** `python -m bandit -r carecast -s B404`
- **Output:** Clean exit (code 0). 0 issues identified across 1,677 lines of code.
- **Note:** Git commit resolution in `carecast/pipeline.py` hardened using `shutil.which("git")` with static command list `[git_bin, "rev-parse", "HEAD"]`.

### B. Secret Scan
- **Command:** `git grep -nEi "(api[_-]?key|secret|token|passwd|password|bearer|private[_-]?key)" -- . ":(exclude)docs" ":(exclude)reports"`
- **Output:** Clean — 0 secrets found.

### C. SQL Injection AST Guard (AT-05)
- **Command:** `pytest -v tests/unit/test_sql_guard.py`
- **Output:** PASSED — Verified all SQLite query invocations across `carecast/` are static strings with parameterized arguments.

---

## 3. What Was Changed and Why
- Hardened git commit extraction in `carecast/pipeline.py` using `shutil.which("git")` to prevent PATH hijacking or untrusted binary execution (Bandit B607/B603).
- Bounded prediction intervals in `carecast/evaluate.py` and `carecast/pipeline.py` to ensure `lower <= point <= upper` and `lower >= 0.0` under all empirical residual distributions, strictly satisfying database CHECK constraints.
- Verified absence of pickle/joblib serialization: all models are fitted deterministically on-the-fly and stored only as metadata and metrics, eliminating deserialization vulnerabilities.

---

## 4. Residual Risks
- Model predictions reflect historical CDC epidemiological data and must never be interpreted as clinical diagnoses or medical advice (governed by PRD disclaimers D-01, D-02).
- No web UI exists at this phase; screenshot evidence is not applicable ("no UI at this phase").
