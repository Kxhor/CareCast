# CareCast — Complete Project Trajectory & Conversation Record (Phases 1–3)

**Project Name:** CareCast — Explainable Respiratory Admission Forecasting & Capacity Early Warning  
**Context:** Undergraduate engineering capstone project (decision support only; explicitly NOT clinically validated).  
**Source of Truth:** The 8 system documents in `docs/` (`PRD.md`, `TRD.md`, `APP_FLOW.md`, `UI_UX_DESIGN.md`, `BACKEND_SCHEMA.md`, `IMPLEMENTATION_PLAN.md`, `ANTIGRAVITY_PROMPTS.md`, `FINAL_PROJECT_AUDIT.md`).  
**Current Branch / Head:** `master` at commit `3bc2ce2`  
**Latest Approved Tag:** `phase-3-approved`  

---

## 1. Operating Protocol & Governing Principles (Rule G-0)

Throughout development, the agent and developer adhered strictly to Rule G-0:
1. **Inspect First:** Before making changes, examine files, verify environment, read required docs, and confirm active state.
2. **One Phase at a Time:** Deliver and validate only the active phase. Never jump ahead to future phases. Stop and wait for the exact approval gate message: `APPROVED: PHASE <N>`.
3. **Evidence, Not Claims:** All assertions backed by real terminal command execution and recorded raw logs in `reports/logs/`. Zero fabricated numbers.
4. **Zero New Dependencies:** Maintain strict fidelity to `requirements.txt` / `requirements-dev.txt`.
5. **Security Reviews:** Perform incremental security reviews (`SR-1`, `SR-2`, etc.) after each phase adhering to the Master Security Checklist.
6. **Machine Learning Honesty:**
   - Chronological 60/20/20 train/valid/test splits on target weeks only.
   - Walk-forward evaluation strictly leak-free ($s+h \le t$).
   - Model selection performed strictly on the validation block.
   - No tuning on the test block.
   - Compare all candidates against naive persistence baselines.
   - Report raw metrics honestly—plainly state when models do not beat persistence.
   - No pickle/joblib serialization; models fit deterministically in-memory.

---

## 2. Chronological Trajectory of Completed Work

### Phase 1: Foundation, Skeleton & Database Migrations
- **Objective:** Establish clean workspace skeleton, SQLite read-only / read-write connection isolation, database migration runner, and initial schema.
- **Key Deliverables:**
  - `carecast/settings.py`: Pydantic settings loading `.env` and `config/carecast.toml` (validating environment, logging, rate limits).
  - `carecast/db.py`: Dual-mode connection manager:
    - `connect_rw(db_path)`: Write-enabled connection with WAL mode and `PRAGMA foreign_keys = ON`.
    - `connect_ro(db_path)`: Read-only URI connection (`file:...mode=ro`) strictly rejecting write operations.
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
    - Computes file SHA-256 for audit traceability.
    - Idempotent ingestion: re-running ingestion detects existing SHA-256 and inserts 0 new rows (AT-01).
    - Checks required logical columns; aborts with clear error if missing (AT-02).
  - **Data Quality & Hygiene (`carecast/quality.py`):**
    - Validates Saturday dates, non-negative admission counts, and contiguous calendar weeks.
    - Logs data defects (missing weeks, duplicate rows, gaps) into T6 (`data_quality_issues`) without crashing pipeline (AT-03).
  - **Pipeline CLI (`carecast/pipeline.py`):** Added subcommands `migrate`, `ingest`, and `check`.
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
    - AT-08 Leakage Test: verified that modifying/corrupting data after origin $t$ leaves features and predictions at $t$ unchanged.
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
    - Metadata logging in `config_json`: config hash, scikit-learn/pandas/numpy versions, raw CSV SHA-256, git commit hash, clipping notes.
  - **Verification & Reproducibility (AT-43):**
    - Full pytest suite: 43/43 tests passed in 17.09s (`reports/logs/p3-pytest.txt`).
    - Two sequential training runs produced bit-exact identical evaluation metrics (zero diff across all 96 metric records in `reports/logs/p3-reproducibility-diff.txt`).
  - **Security Review (`reports/security/SR-2.md`):**
    - Bandit security scan clean (0 issues).
    - Secret scan clean (0 secrets).
    - Hardened git subprocess execution using `shutil.which("git")`.
- **Commit & Gate:** Tagged as `phase-3-approved` at commit `3bc2ce2`.

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

*Key Takeaway:* Models demonstrated significant improvements over persistence on the validation block (e.g. COVID $h=1$ validation MAE was 440.49 vs 785.26, a 44% improvement). However, during the test block (representing low-variance off-season summer weeks), persistence proved extraordinarily difficult to beat. Following scientific integrity standards, this is acknowledged plainly and without test tuning.

---

## 4. Current State & Next Phase

- **Completed Phases:** Phase 1, Phase 2, Phase 3.
- **Git Tags:** `phase-1-approved`, `phase-2-approved`, `phase-3-approved`.
- **Database Status:** `data/carecast.db` contains complete observations, quality issue logs, model runs (Flu run 5, COVID-19 run 6, RSV run 7 as current), backtests, forecasts, and contributions.
- **Pending Phase:** **PHASE 4 — Backend API & Planning Logic (Features F2, F5, F7, F8, F9, F10, F11)**.
  - Pure planning logic functions (`carecast/planning.py`).
  - Read-only FastAPI service (`carecast/api/`).
  - Endpoints E1 through E8.
  - Security middleware: security response headers, rate limiting, generic safe error responses.
  - Acceptance tests AT-06, AT-09, AT-15, AT-16, AT-21, AT-22, AT-24, AT-26, AT-28, AT-30, AT-33, AT-34, AT-35, AT-37.
  - Incremental Security Review `SR-3`.
