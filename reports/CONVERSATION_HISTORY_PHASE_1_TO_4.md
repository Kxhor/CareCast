# CareCast — Complete Technical Trajectory & Conversation Record (Phases 1–4)

**Project Name:** CareCast — Explainable Respiratory Admission Forecasting & Capacity Early Warning  
**Context:** Undergraduate engineering capstone project (decision support only; explicitly NOT clinically validated).  
**Source of Truth:** The 8 system documents in `docs/` (`PRD.md`, `TRD.md`, `APP_FLOW.md`, `UI_UX_DESIGN.md`, `BACKEND_SCHEMA.md`, `IMPLEMENTATION_PLAN.md`, `ANTIGRAVITY_PROMPTS.md`, `FINAL_PROJECT_AUDIT.md`).  
**Current Branch / Status:** `master` at commit `3bc2ce2` with Phase 4 completed and verified (99 tests passing, contract snapshot baseline locked).  
**Phase Gates Completed:** `phase-1-approved`, `phase-2-approved`, `phase-3-approved`, Phase 4 complete and ready for approval.  

---

## 1. Operating Protocol & Governing Principles (Rule G-0)

Throughout development, the engineering and auditing process adhered strictly to Rule G-0:
1. **Inspect First:** Before making any change, examine files, verify environment, read required system specs, and confirm active state.
2. **One Phase at a Time:** Deliver and validate strictly the active phase. Never jump ahead to future phases. Stop and wait for the exact approval gate message: `APPROVED: PHASE <N>`.
3. **Evidence, Not Claims:** All assertions backed by real terminal command execution and recorded raw logs in `reports/logs/`. Zero fabricated numbers.
4. **Zero New Dependencies:** Maintain strict fidelity to `requirements.txt` / `requirements-dev.txt`.
5. **Security Reviews:** Perform incremental security reviews (`SR-1`, `SR-2`, `SR-3`, etc.) after each phase adhering to the Master Security Checklist.
6. **Machine Learning Honesty:**
   - Chronological 60/20/20 train/valid/test splits on target weeks only.
   - Walk-forward evaluation strictly leak-free ($s+h \le t$).
   - Model selection performed strictly on the validation block.
   - Zero tuning on the test block.
   - Compare all candidates against naive persistence baselines.
   - Report raw metrics honestly—plainly state when models do not beat persistence.
   - Zero pickle/joblib serialization; models fit deterministically in-memory.

---

## 2. Chronological Trajectory of Completed Work

### Phase 1: Foundation, Skeleton & Database Migrations
- **Objective:** Establish clean workspace skeleton, SQLite read-only / read-write connection isolation, database migration runner, and initial schema.
- **Key Deliverables:**
  - `carecast/settings.py`: Pydantic settings loading `.env` and `config/carecast.toml` (validating environment, logging, rate limits).
  - `carecast/db.py`: Dual-mode connection manager:
    - `connect_rw(db_path)`: Write-enabled connection with WAL mode and `PRAGMA foreign_keys = ON`.
    - `connect_ro(db_path)`: Read-only URI connection (`file:...mode=ro`) with `PRAGMA query_only = ON` strictly rejecting write operations.
  - `migrations/0001_core_data.sql`: Core schema tables:
    - T1: `schema_migrations`
    - T2: `dataset_sources`
    - T3: `jurisdictions`
    - T4: `diseases`
    - T5: `weekly_observations` (with CHECK constraint enforcing Saturday dates: `strftime('%w', week_end_date) = '6'`)
    - T6: `data_quality_issues`
  - `migrations/0002_forecasting.sql`: Forecasting schema tables:
    - T7: `model_runs` (with CHECK constraint enforcing chronological splits: `train_start <= train_end < valid_start <= valid_end < test_start <= test_end`)
    - T8: `evaluation_metrics`
    - T9: `backtest_predictions`
    - T10: `forecasts` (with CHECK constraint: `lower <= point AND point <= upper` and `lower >= 0`)
    - T11: `feature_contributions`
  - Unit tests for DB connection isolation, migrations, settings, and smoke imports.
- **Commit & Gate:** Tagged as `phase-1-approved` at commit `1a02fa0`.

---

### Phase 2: Data Acquisition, Validation & Pipeline Ingest (Feature F1)
- **Objective:** Ingest public CDC respiratory datasets, enforce data quality, prevent SQL injection via AST guards, and verify privacy constraints.
- **Key Deliverables:**
  - **Data Ingestion (`carecast/ingest.py`):**
    - Parses and maps CDC NHSN CSV datasets (`ua7e-t2fy.csv` primary, `vdzy-6i9v.csv` secondary) using `config/dataset_mapping.toml`.
    - Computes file SHA-256 for audit traceability (`cdbde5be30e3ae2fa57deb323da68d0364ebb43ea5dcc3b5f88987fbcd979ebc`).
    - Idempotent ingestion: re-running ingestion detects existing SHA-256 and inserts 0 new rows (AT-01).
    - Checks required logical columns; aborts with clear error if missing (AT-02).
  - **Data Quality & Hygiene (`carecast/quality.py`):**
    - Validates Saturday dates, non-negative admission counts, and contiguous calendar weeks.
    - Logs data defects (missing weeks, duplicate rows, gaps) into T6 (`data_quality_issues`) without crashing pipeline (AT-03).
  - **Pipeline CLI (`carecast/pipeline.py`):** Subcommands `migrate`, `ingest`, and `check`.
  - **Security & Quality Guards:**
    - `tests/unit/test_sql_guard.py`: Static AST inspection ensuring zero dynamic SQL queries built with f-strings, `%`, or `.format` (AT-05).
    - `tests/unit/test_schema_constraints.py`: Privacy audit (AT-45) proving zero patient-level fields (`patient_id`, `ssn`, `mrn`, etc.) exist in the schema.
    - Negative constraint tests validating SQLite CHECK constraints.
  - **Reports Generated:**
    - `reports/eda_summary.md`: Exploratory Data Analysis of CDC datasets across Flu, COVID-19, and RSV.
    - `reports/security/SR-1.md`: Incremental Security Review 1 (Bandit clean, secret scan clean).
    - `reports/phase-2.md`: Phase 2 report.
- **Commit & Gate:** Tagged as `phase-2-approved` at commit `5e23ce3`.

---

### Phase 3: Forecast Engine & Evaluation (Features F3, F4, F6, F12)
- **Objective:** Build reproducible multi-horizon forecasting, chronological walk-forward evaluation, empirical interval calculation, and feature explainability.
- **Key Deliverables:**
  - **Configuration (`config/pipeline.toml`):**
    - Splits: 60% train, 20% validation, 20% test.
    - Horizons: 1, 2, 3, 4 weeks.
    - Interval Level: 80% ($q_{10}$ to $q_{90}$).
    - Threshold: 75th percentile of training block.
    - Random Seed: 42.
    - Training start dates: `2022-10-01` (Flu, COVID-19) and `2023-10-07` (RSV inception).
  - **Features (`carecast/features.py`):**
    - Features: $y_{\text{lag0}}\dots y_{\text{lag3}}$, $\text{roll\_mean\_4}$, $\text{seasonal\_lag52}$ (where history allows), cyclical $\sin/\cos$ of target week-of-year, and $\text{pct\_reporting}$.
    - AT-08 Leakage Test: verified that modifying data after origin $t$ leaves features and predictions at $t$ unchanged.
  - **Models (`carecast/models.py`):**
    - `baseline_persistence`: predicts $y_{\text{lag0}}$.
    - `baseline_seasonal_naive`: predicts $\text{seasonal\_lag52}$.
    - `linear_lag`: Linear regression on lag and seasonal features.
    - `hgb_lag`: HistGradientBoostingRegressor with fixed random state.
    - Non-negative prediction clipping: all negative outputs clipped to 0.0 with documentation in metadata.
  - **Walk-Forward Evaluation (`carecast/evaluate.py`):**
    - Chronological 60/20/20 partitioning on target weeks (AT-11).
    - Walk-forward training restriction: training origins $s$ satisfy $s+h \le t$.
    - Validation-only model selection per horizon based on lowest validation MAE.
    - Signed validation residual quantiles ($q_{10}$ clamped $\le 0$, $q_{90}$ clamped $\ge 0$) to generate calibrated 80% prediction intervals bounded by $[0, \infty)$.
    - Evaluates test interval coverage and test `beats_persistence` verdict.
  - **Explainability (`carecast/explain.py`):**
    - Additive linear contribution: $\text{contrib}_j = \text{coef}_j \times (x_j - \bar{x}_{\text{train}, j})$ with $\text{base} = \bar{y}_{\text{train}}$.
    - AT-18 Additive Identity: $|\text{base} + \sum \text{contrib}_j - \text{prediction}| < 10^{-9}$.
    - Permutation importance on the validation block with negative MAE scoring.
    - AT-19 Non-Causal Plain-Language Text: uses "associated with" terminology; zero causal verbs.
  - **Pipeline Orchestrator (`carecast/pipeline.py`):**
    - Added `cmd_train` executing full walk-forward evaluation and final refits.
    - Transaction isolation: single transaction per series (`BEGIN TRANSACTION;` $\dots$ `COMMIT;`).
    - Version rollover: sets prior runs `is_current = 0`, newest `is_current = 1`.
    - Metadata logging in `config_json`: config hash, library versions, raw CSV SHA-256, git commit hash, clipping notes.
  - **Verification & Reproducibility (AT-43):**
    - Full pytest suite: 43/43 tests passed in 17.09s (`reports/logs/p3-pytest.txt`).
    - Two sequential training runs produced bit-exact identical evaluation metrics (zero diff across all 96 metric records in `reports/logs/p3-reproducibility-diff.txt`).
  - **Security Review (`reports/security/SR-2.md`):**
    - Bandit security scan clean (0 issues). Secret scan clean (0 secrets).
    - Hardened git subprocess execution using `shutil.which("git")`.
- **Commit & Gate:** Tagged as `phase-3-approved` at commit `3bc2ce2`.

---

### Phase 4: Backend API & Planning Logic (Features F2, F5, F7, F8, F9, F10, F11)
- **Objective:** Read-only JSON API (E1–E8), pure domain planning functions, hardened HTTP layer, and OpenAPI contract snapshot.
- **Key Deliverables:**
  - **Pure Planning Functions (`carecast/planning.py`):**
    - `calculate_tier(point, lower, upper, threshold)` per PRD F5.2 / AT-15.
    - `calculate_scenario(base_point, base_lower, base_upper, surge_pct)` per PRD F7.1 / AT-21.
    - `calculate_capacity_illustration(...)` per PRD F8.2 / AT-24; safely handles `reference_level <= 0`.
    - `get_action_checklist(tier, actions_config)` per PRD F9.1-F9.2 / AT-26 with mandatory non-clinical governance footer.
    - `format_explanation_text(...)` per PRD F6.3 / AT-19 with strict non-causal language.
  - **Configuration (`config/planning.toml`):**
    - Neutral capacity placeholders labelled `note = "DEMO PLACEHOLDER — not data"`.
    - Input bounds, action checklists, verbatim limitations L-01 to L-12, and disclaimers.
  - **REST API Endpoints E1–E8 (`carecast/api/routes.py`, `schemas.py`):**
    - E1: `GET /api/v1/health`
    - E2: `GET /api/v1/meta`
    - E3: `GET /api/v1/summary`
    - E4: `GET /api/v1/observations`
    - E5: `GET /api/v1/forecast`
    - E6: `GET /api/v1/evaluation`
    - E7: `GET /api/v1/explain`
    - E8: `POST /api/v1/scenario`
    - All Pydantic models configured with `ConfigDict(extra="forbid")`.
    - Enums and parameters validated against SQLite reference tables.
    - Parameterised SQL queries only with safe target column allowlist (`TARGET_ALLOWLIST`).
    - API runs strictly over `connect_ro(mode=ro, query_only=ON)` — write attempts fail with SQLite operational error.
  - **HTTP Hardening & Security Middleware (`carecast/api/main.py`, `ratelimit.py`):**
    - Injected security headers on all responses (CSP with `frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, `Permissions-Policy`, and `Cache-Control: no-store` on API routes).
    - Strict absence of CORS middleware and cookies (zero `Access-Control-*`, zero `Set-Cookie`).
    - Server-side generated `X-Request-ID` UUID on all requests and error envelopes.
    - 8 KB body size limit on POST requests (`MAX_BODY_BYTES = 8192` -> HTTP 413 `payload_too_large`).
    - In-memory sliding-window rate limiter per client IP.
    - Generic non-disclosing error envelopes (422 returns field names only; 500 hides traces/paths/SQL).
    - Production docs disabled: `/docs`, `/redoc`, `/openapi.json` return 404 unless `CARECAST_ENV=dev` and `CARECAST_ENABLE_DOCS=1`.
    - Static mount for `web/` with placeholder `index.html`.
  - **Contract Snapshot (`tests/contract/openapi.snapshot.json`):**
    - Dumped from `app.openapi()` via `scripts/generate_openapi_snapshot.py`.
    - Verified by automated regression test `test_openapi_contract.py` (AT-47).
    - Baseline SHA-256 locked: `f083424340a1973ccdf07e975729156564207ff44109b8a4459f011a677b4259`.
  - **Verification & Testing:**
    - Full pytest suite: **99 passed, 0 failures, 17 warnings** in 9.71s (`reports/logs/p4-pytest.txt`).
    - Live manual `curl` execution against real database captured in `reports/logs/p4-curl-endpoints.txt`.
  - **Security Review (`reports/security/SR-3.md`):**
    - Bandit security scan clean (0 issues across 3,471 LOC).
    - Secret scan clean (0 secrets).
    - SQL AST guard clean (zero dynamic SQL).
  - **Report Generated:** `reports/phase-4.md`.

---

## 3. Real Walk-Forward Evaluation Results Summary

| Series | Horizon ($h$) | Selected Model | Validation MAE | Test MAE | Persistence Test MAE | Rel. Test MAE | Test Coverage | Beats Persistence? |
|:---|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Flu** | 1 | `linear_lag` | 1,755.37 | 595.73 | 564.76 | 1.055 | 97.0% | **0 (NO)** |
| **Flu** | 2 | `linear_lag` | 4,758.21 | 1,352.93 | 1,090.61 | 1.241 | 100.0% | **0 (NO)** |
| **Flu** | 3 | `hgb_lag` | 6,193.38 | 3,272.48 | 1,587.82 | 2.061 | 100.0% | **0 (NO)** |
| **Flu** | 4 | `hgb_lag` | 6,132.30 | 4,141.54 | 2,103.70 | 1.969 | 100.0% | **0 (NO)** |
| **COVID-19** | 1 | `linear_lag` | 440.49 | 325.57 | 294.00 | 1.107 | 21.2% | **0 (NO)** |
| **COVID-19** | 2 | `linear_lag` | 1,088.64 | 726.31 | 568.76 | 1.277 | 9.1% | **0 (NO)** |
| **COVID-19** | 3 | `linear_lag` | 1,727.67 | 1,043.40 | 831.03 | 1.256 | 15.2% | **0 (NO)** |
| **COVID-19** | 4 | `linear_lag` | 2,122.80 | 1,288.34 | 1,108.12 | 1.163 | 15.2% | **0 (NO)** |
| **RSV** | 1 | `linear_lag` | 509.91 | 171.25 | 83.14 | 2.060 | 100.0% | **0 (NO)** |
| **RSV** | 2 | `linear_lag` | 1,047.82 | 311.32 | 171.86 | 1.812 | 100.0% | **0 (NO)** |
| **RSV** | 3 | `linear_lag` | 1,673.35 | 372.06 | 280.19 | 1.328 | 100.0% | **0 (NO)** |
| **RSV** | 4 | `hgb_lag` | 1,959.35 | 564.78 | 377.24 | 1.497 | 100.0% | **0 (NO)** |

*Scientific Integrity Note:* Models demonstrated significant improvements over persistence on the validation block. On the held-out test block (low-variance off-season summer weeks), persistence proved hard to beat. Per Rule G-0, this is recorded honestly without test-block tuning.

---

## 4. Complete Acceptance Test Catalog & Status (Phases 1–4)

| AT | Feature / NFR | Test Condition | Phase | Status | Evidence |
|---|---|---|---|:---:|---|
| **AT-01** | F1 | Ingest idempotency (2nd run inserts 0) | P2 | PASS | `test_ingest.py` |
| **AT-02** | F1 | Missing/renamed required column aborts with error | P2 | PASS | `test_ingest.py` |
| **AT-03** | F1 | Data defects detected and logged to T6 | P2 | PASS | `test_ingest.py`, `test_quality.py` |
| **AT-04** | F1 | Raw file SHA-256 recorded and immutable | P2 | PASS | `test_ingest.py` |
| **AT-05** | F1/N1 | AST guard: no SQL built via f-string/%/.format | P2–P7 | PASS | `test_sql_guard.py` |
| **AT-06** | F2 | `GET /observations` ascending dates; from > to -> 422 | P4 | PASS | `test_api_endpoints.py` |
| **AT-08** | F3 | Leakage perturbation test: post-$t$ changes leave $t$ unchanged | P3 | PASS | `test_features.py` |
| **AT-09** | F3 | `GET /forecast` returns 4 horizons ascending; lower <= point <= upper | P4 | PASS | `test_api_endpoints.py` |
| **AT-10** | F3/F4 | Empirical interval coverage computed, stored, and exposed | P3, P4 | PASS | `test_storage.py`, `test_api_endpoints.py` |
| **AT-11** | F4 | Chronological split ordering `train < valid < test` enforced in DB DDL | P3 | PASS | `test_evaluate.py`, `test_schema_constraints.py` |
| **AT-12** | F4 | Baseline persistence and seasonal naive match hand calculations | P3 | PASS | `test_models.py` |
| **AT-13** | F4 | MAE/RMSE calculations match hand/sklearn fixtures | P3 | PASS | `test_evaluate.py` |
| **AT-14** | F4 | Verdict text: "improves" iff test MAE(selected) < MAE(persistence) | P3, P4 | PASS | `test_evaluate.py`, `test_api_endpoints.py` |
| **AT-15** | F5 | Boundary table: point==threshold -> Watch; point>threshold -> Elevated; upper==threshold -> Normal | P4 | PASS | `test_planning.py` |
| **AT-16** | F5 | Non-numeric, negative, NaN/inf, > bound threshold -> 422 | P4 | PASS | `test_api_endpoints.py` |
| **AT-18** | F6 | Additive identity: $\text{base} + \sum \text{contrib} = \text{pred}$ ($|\Delta| < 10^{-9}$) | P3 | PASS | `test_explain.py` |
| **AT-19** | F6 | Plain language explanation text uses non-causal language | P4 | PASS | `test_planning.py`, `test_api_endpoints.py` |
| **AT-21** | F7 | Scenario scaling `adjusted = base * (1 + pct/100)` | P4 | PASS | `test_planning.py` |
| **AT-22** | F7 | `surge_pct` outside $[-50, 100]$ returns 422 | P4 | PASS | `test_api_endpoints.py` |
| **AT-24** | F8 | Capacity illustration worked example yields exact formula values | P4 | PASS | `test_planning.py` |
| **AT-25** | F8 | `is_simulated = true` exposed in API | P4 | PASS | `test_api_endpoints.py` |
| **AT-26** | F9 | Deterministic tier action checklists ending with governance footer | P4 | PASS | `test_planning.py` |
| **AT-28** | F10 | `/meta` returns provenance, SHA-256, data-as-of, disclaimers, L-01..12 | P4 | PASS | `test_api_endpoints.py` |
| **AT-30** | F11 | `/summary` returns latest, next-week forecast, tier, and watchlist | P4 | PASS | `test_api_endpoints.py` |
| **AT-33** | N1 | Security response headers (CSP, nosniff, Referrer-Policy, DENY) | P4 | PASS | `test_api_security.py` |
| **AT-34** | N1 | Forced server error returns generic JSON; zero traceback/path/SQL leak | P4 | PASS | `test_api_security.py` |
| **AT-35** | N1 | Exceeding rate limit returns HTTP 429 with `Retry-After` header | P4 | PASS | `test_api_security.py` |
| **AT-37** | N1 | Zero `Access-Control-Allow-*` and zero `Set-Cookie` headers | P4 | PASS | `test_api_security.py` |
| **AT-43** | N2 | Pipeline re-run reproduces bit-exact identical metrics | P3 | PASS | `p3-reproducibility-diff.txt` |
| **AT-45** | N6 | Privacy schema audit: zero patient-level or PII fields in DB | P2 | PASS | `test_schema_constraints.py` |
| **AT-47** | N1 | OpenAPI specification contract snapshot matches `app.openapi()` | P4 | PASS | `test_openapi_contract.py` |

---

## 5. Security Reviews & Hardening Ledger

- **SR-1 (Phase 2):** Ingest and DB safety. Bandit clean, secret scan clean, SQL AST guard passed, schema privacy audit passed.
- **SR-2 (Phase 3):** ML and pipeline safety. Deterministic random seeds, zero pickle/joblib serialization, non-negative clipping, hardened git commit extraction via `shutil.which("git")`. Bandit clean, secret scan clean.
- **SR-3 (Phase 4):** Backend API and HTTP hardening.
  - Read-only SQLite connection URI (`connect_ro`, `mode=ro`, `PRAGMA query_only = ON`).
  - Strict security response headers (CSP with `frame-ancestors 'none'`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`).
  - Server-side request ID UUID generation on all requests and error envelopes.
  - 8 KB body size limit on POST requests (`MAX_BODY_BYTES = 8192` -> HTTP 413).
  - In-memory sliding-window rate limiter per client IP.
  - Pydantic models with `ConfigDict(extra="forbid")` rejecting unknown fields with HTTP 422.
  - Production docs disabled (`/docs`, `/redoc`, `/openapi.json` return 404 in prod).
  - Bandit clean (0 issues across 3,471 LOC). Secret scan clean (0 secrets).

---

## 6. Current Baseline for Phase 5 (Frontend Core Build)

Before beginning Phase 5 frontend coding, the regression baseline is locked:
- **Backend Test Suite Baseline:** **99 passed, 0 failures, 17 warnings** in 9.71s (`reports/logs/p4-pytest.txt`).
- **OpenAPI Contract Snapshot Baseline SHA-256:**
  ```text
  f083424340a1973ccdf07e975729156564207ff44109b8a4459f011a677b4259
  ```
- **Backend Invariance Rule (Regression R1):** In Phase 5, frontend code must NOT touch or modify any backend file. After Phase 5, the backend test suite must pass with 99 tests and the contract snapshot hash must be identical.
