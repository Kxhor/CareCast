# BACKEND_SCHEMA — Database, Data Contract & API

| Field | Value |
|---|---|
| Document | `docs/BACKEND_SCHEMA.md` (5 of 8) |
| Version / status | 1.0 — **DRAFT FOR USER APPROVAL** |
| Date | 10 Oct 2026 |
| Depends on | [PRD](PRD.md) · [TRD](TRD.md) |
| Important | All JSON examples are **ILLUSTRATIVE shapes with placeholder values**. They are *not* data, results or expected metrics. |

---

## 1. Data contract (logical fields → CDC columns)

CDC column names are **⚠️ TO-VERIFY in P2**. The pipeline reads a **mapping file**, so a wrong guess fails loudly instead of silently.

| Logical field | Type | Required | Validation | Maps to (filled in P2) |
|---|---|---|---|---|
| `week_end_date` | ISO date | ✅ | Parses; **Saturday** (`strftime('%w')='6'`); no future dates | `date_column` |
| `jurisdiction` | text | ✅ | Mapped to canonical code (`US` = national) | `jurisdiction_column` + `[jurisdictions]` map |
| `disease` | enum `flu \| covid19 \| rsv` | ✅ | One column set per disease | `[diseases.<code>]` |
| `admissions_count` | real ≥ 0 | one of count/rate | Numeric; ≥ 0 | `count_column` |
| `admissions_rate_per_100k` | real ≥ 0 | one of count/rate | Numeric; ≥ 0 | `rate_column` |
| `admission_level` | text | optional | Stored verbatim for context | `level_column` |
| `reporting_hospitals` | integer ≥ 0 | optional | Numeric | `reporting_hospitals_column` |
| `pct_reporting` | real 0–100 | optional | Within 0–100 | `pct_reporting_column` |

Rules: reject (abort) if a *required* mapped column is absent; coerce non-numeric to NULL **and** log to T6; never silently drop rows.

---

## 2. Entity-relationship overview

```
dataset_sources (T2) 1 ──< weekly_observations (T5) >── 1 jurisdictions (T3)
        │                              └──────────── >── 1 diseases (T4)
        └──< data_quality_issues (T6)

dataset_sources 1 ──< model_runs (T7) >── 1 jurisdictions / diseases
model_runs 1 ──< evaluation_metrics (T8)
model_runs 1 ──< backtest_predictions (T9)
model_runs 1 ──< forecasts (T10)
model_runs 1 ──< feature_contributions (T11)
schema_migrations (T1) — bookkeeping
```

---

## 3. DDL

### 3.1 `migrations/0001_core_data.sql` (T1–T6 + seeds)

```sql
PRAGMA foreign_keys = ON;

-- T1
CREATE TABLE schema_migrations (
  version    TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- T2
CREATE TABLE dataset_sources (
  id           INTEGER PRIMARY KEY,
  name         TEXT NOT NULL,
  publisher    TEXT NOT NULL,
  dataset_id   TEXT NOT NULL,                       -- e.g. the data.cdc.gov id (verified in P2)
  url          TEXT NOT NULL,
  licence_note TEXT,
  retrieved_at TEXT NOT NULL,                       -- ISO-8601 UTC
  file_name    TEXT NOT NULL,
  file_sha256  TEXT NOT NULL CHECK (length(file_sha256) = 64),
  row_count    INTEGER NOT NULL CHECK (row_count >= 0),
  notes        TEXT,
  UNIQUE (dataset_id, file_sha256)
);

-- T3
CREATE TABLE jurisdictions (
  code  TEXT PRIMARY KEY,                           -- canonical; 'US' = national
  name  TEXT NOT NULL,
  level TEXT NOT NULL CHECK (level IN ('national','state','territory'))
);

-- T4
CREATE TABLE diseases (
  code  TEXT PRIMARY KEY CHECK (code IN ('flu','covid19','rsv')),
  label TEXT NOT NULL
);

-- T5
CREATE TABLE weekly_observations (
  id                        INTEGER PRIMARY KEY,
  source_id                 INTEGER NOT NULL REFERENCES dataset_sources(id),
  jurisdiction_code         TEXT    NOT NULL REFERENCES jurisdictions(code),
  disease_code              TEXT    NOT NULL REFERENCES diseases(code),
  week_end_date             TEXT    NOT NULL CHECK (strftime('%w', week_end_date) = '6'),
  admissions_count          REAL    CHECK (admissions_count IS NULL OR admissions_count >= 0),
  admissions_rate_per_100k  REAL    CHECK (admissions_rate_per_100k IS NULL OR admissions_rate_per_100k >= 0),
  admission_level           TEXT,
  reporting_hospitals       INTEGER CHECK (reporting_hospitals IS NULL OR reporting_hospitals >= 0),
  pct_reporting             REAL    CHECK (pct_reporting IS NULL OR (pct_reporting >= 0 AND pct_reporting <= 100)),
  is_imputed                INTEGER NOT NULL DEFAULT 0 CHECK (is_imputed IN (0,1)),
  CHECK (admissions_count IS NOT NULL OR admissions_rate_per_100k IS NOT NULL),
  UNIQUE (jurisdiction_code, disease_code, week_end_date)
);

-- T6
CREATE TABLE data_quality_issues (
  id                INTEGER PRIMARY KEY,
  source_id         INTEGER NOT NULL REFERENCES dataset_sources(id),
  jurisdiction_code TEXT REFERENCES jurisdictions(code),
  disease_code      TEXT REFERENCES diseases(code),
  check_name        TEXT NOT NULL,       -- duplicate_key | missing_week | negative_value | non_numeric | non_saturday | coverage_out_of_range | unexpected_code | long_gap | imputed
  severity          TEXT NOT NULL CHECK (severity IN ('info','warning','error')),
  detail            TEXT NOT NULL,
  week_start        TEXT,
  week_end          TEXT,
  detected_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX ix_quality_source_sev ON data_quality_issues (source_id, severity);

-- Seeds (reference data only — see §6)
INSERT INTO diseases (code, label) VALUES
  ('flu','Influenza'), ('covid19','COVID-19'), ('rsv','RSV');
INSERT INTO jurisdictions (code, name, level) VALUES
  ('US','United States (national)','national');

INSERT INTO schema_migrations (version) VALUES ('0001_core_data');
```

### 3.2 `migrations/0002_forecasting.sql` (T7–T11 + view)

```sql
PRAGMA foreign_keys = ON;

-- T7
CREATE TABLE model_runs (
  id                       INTEGER PRIMARY KEY,
  created_at               TEXT NOT NULL,
  jurisdiction_code        TEXT NOT NULL REFERENCES jurisdictions(code),
  disease_code             TEXT NOT NULL REFERENCES diseases(code),
  source_id                INTEGER NOT NULL REFERENCES dataset_sources(id),
  target_kind              TEXT NOT NULL CHECK (target_kind IN ('count','rate')),
  data_end_date            TEXT NOT NULL,
  train_start              TEXT NOT NULL,  train_end  TEXT NOT NULL,
  valid_start              TEXT NOT NULL,  valid_end  TEXT NOT NULL,
  test_start               TEXT NOT NULL,  test_end   TEXT NOT NULL,
  n_train                  INTEGER NOT NULL CHECK (n_train > 0),
  n_valid                  INTEGER NOT NULL CHECK (n_valid > 0),
  n_test                   INTEGER NOT NULL CHECK (n_test > 0),
  interval_level           REAL NOT NULL CHECK (interval_level > 0 AND interval_level < 1),
  default_threshold        REAL NOT NULL CHECK (default_threshold >= 0),
  default_threshold_method TEXT NOT NULL,           -- e.g. 'percentile_75_of_training_block'
  reference_level          REAL NOT NULL CHECK (reference_level >= 0),   -- mean of last 4 observed weeks (F8)
  random_seed              INTEGER NOT NULL,
  config_json              TEXT NOT NULL,           -- config + library versions + clipping notes
  data_sha256              TEXT NOT NULL CHECK (length(data_sha256) = 64),
  code_version             TEXT NOT NULL,
  is_current               INTEGER NOT NULL DEFAULT 0 CHECK (is_current IN (0,1)),
  CHECK (train_start <= train_end AND train_end < valid_start AND valid_start <= valid_end
         AND valid_end < test_start AND test_start <= test_end)     -- AT-11 enforced in the DB
);
CREATE UNIQUE INDEX ux_model_runs_current
  ON model_runs (jurisdiction_code, disease_code) WHERE is_current = 1;

-- T8
CREATE TABLE evaluation_metrics (
  id                  INTEGER PRIMARY KEY,
  run_id              INTEGER NOT NULL REFERENCES model_runs(id) ON DELETE CASCADE,
  horizon_weeks       INTEGER NOT NULL CHECK (horizon_weeks BETWEEN 1 AND 4),
  model_name          TEXT NOT NULL CHECK (model_name IN
                        ('baseline_persistence','baseline_seasonal_naive','linear_lag','hgb_lag')),
  split               TEXT NOT NULL CHECK (split IN ('validation','test')),
  mae                 REAL NOT NULL CHECK (mae  >= 0),
  rmse                REAL NOT NULL CHECK (rmse >= 0),
  n_eval              INTEGER NOT NULL CHECK (n_eval > 0),
  mae_vs_persistence  REAL,                         -- model MAE / persistence MAE (same split); NULL if persistence MAE = 0
  is_selected         INTEGER NOT NULL DEFAULT 0 CHECK (is_selected IN (0,1)),
  interval_coverage   REAL CHECK (interval_coverage IS NULL OR (interval_coverage BETWEEN 0 AND 1)),  -- selected, test only
  beats_persistence   INTEGER CHECK (beats_persistence IS NULL OR beats_persistence IN (0,1)),        -- selected, test only
  UNIQUE (run_id, horizon_weeks, model_name, split)
);
CREATE INDEX ix_metrics_run ON evaluation_metrics (run_id);

-- T9
CREATE TABLE backtest_predictions (
  run_id               INTEGER NOT NULL REFERENCES model_runs(id) ON DELETE CASCADE,
  model_name           TEXT NOT NULL CHECK (model_name IN
                         ('baseline_persistence','baseline_seasonal_naive','linear_lag','hgb_lag')),
  horizon_weeks        INTEGER NOT NULL CHECK (horizon_weeks BETWEEN 1 AND 4),
  split                TEXT NOT NULL CHECK (split IN ('validation','test')),
  origin_week_end_date TEXT NOT NULL CHECK (strftime('%w', origin_week_end_date) = '6'),
  target_week_end_date TEXT NOT NULL CHECK (strftime('%w', target_week_end_date) = '6'),
  actual               REAL NOT NULL,
  predicted            REAL NOT NULL,
  PRIMARY KEY (run_id, model_name, horizon_weeks, target_week_end_date),
  CHECK (origin_week_end_date < target_week_end_date)
) WITHOUT ROWID;

-- T10
CREATE TABLE forecasts (
  run_id               INTEGER NOT NULL REFERENCES model_runs(id) ON DELETE CASCADE,
  horizon_weeks        INTEGER NOT NULL CHECK (horizon_weeks BETWEEN 1 AND 4),
  origin_week_end_date TEXT NOT NULL,
  target_week_end_date TEXT NOT NULL,
  model_name           TEXT NOT NULL CHECK (model_name IN ('linear_lag','hgb_lag')),
  point                REAL NOT NULL CHECK (point >= 0),
  lower                REAL NOT NULL CHECK (lower >= 0),
  upper                REAL NOT NULL,
  PRIMARY KEY (run_id, horizon_weeks),
  CHECK (lower <= point AND point <= upper),
  CHECK (origin_week_end_date < target_week_end_date)
) WITHOUT ROWID;

-- T11
CREATE TABLE feature_contributions (
  run_id        INTEGER NOT NULL REFERENCES model_runs(id) ON DELETE CASCADE,
  horizon_weeks INTEGER NOT NULL CHECK (horizon_weeks BETWEEN 1 AND 4),
  method        TEXT NOT NULL CHECK (method IN ('linear_contribution','permutation_importance')),
  feature_name  TEXT NOT NULL,                      -- '__base__' allowed for linear_contribution
  value         REAL NOT NULL,
  feature_value REAL,
  PRIMARY KEY (run_id, horizon_weeks, method, feature_name)
) WITHOUT ROWID;

CREATE VIEW v_current_runs AS
  SELECT * FROM model_runs WHERE is_current = 1;

INSERT INTO schema_migrations (version) VALUES ('0002_forecasting');
```

### 3.3 Constraint & index rationale

| Object | Purpose |
|---|---|
| `UNIQUE (jurisdiction_code, disease_code, week_end_date)` | Idempotent ingest (AT-01); also the lookup index for E4 |
| `CHECK strftime('%w')='6'` on dates | Saturday week-ending enforced in DB (AT-03) |
| `CHECK (admissions_count IS NOT NULL OR admissions_rate…)` | A row must carry at least one target |
| `CHECK` ordering on `model_runs` | **Chronological split cannot be violated** (AT-11) |
| Partial unique index `ux_model_runs_current` | Exactly one current run per series |
| `CHECK (lower ≤ point ≤ upper)` on T10 | Matches AT-09 at storage level |
| `ON DELETE CASCADE` T8–T11 | Re-training replaces a run cleanly |
| `WITHOUT ROWID` T9–T11 | Composite natural keys, smaller files |
| `ix_quality_source_sev`, `ix_metrics_run` | S6 and S3 reads |

---

## 4. Permissions model

| Actor | Access | Mechanism |
|---|---|---|
| **Pipeline CLI** (developer) | Read/write DB; read raw CSV | `db.connect_rw()`; file permissions of the dev machine |
| **API process** | **Read-only** DB | `sqlite3.connect("file:<path>?mode=ro", uri=True)` **and** `PRAGMA query_only=ON`; `PRAGMA foreign_keys=ON` |
| **Browser / anonymous user** | Read-only via API (E1–E7); stateless compute (E8) | No DB credentials; no write endpoint exists |
| **Docker runtime** (P7) | DB file read-only for the app user | Image layer file mode `0444`; app runs as **non-root** |

No roles/users table exists (D-04). There is nothing to authorise per-user.

---

## 5. Migrations

| Aspect | Rule |
|---|---|
| Files | `migrations/NNNN_name.sql`, forward-only, applied in lexical order |
| Runner | `python -m carecast.pipeline migrate` — each file in **one transaction**; version inserted into T1; failure rolls back and aborts |
| Idempotency | Already-applied versions are skipped |
| Rollback | **Rebuild** (`python -m carecast.pipeline rebuild`): delete DB → migrate → ingest from `data/raw/` → train. Raw CSVs are the source of truth. |
| Schema changes | New numbered file; never edit an applied migration |
| Horizon change | Changing horizons beyond 1–4 needs a migration to relax `CHECK`s (needs approval) |

---

## 6. Seed data policy

| Data | Seed? | Notes |
|---|---|---|
| `diseases` (3 rows), `jurisdictions` (`US`) | ✅ in migration 0001 | Reference data only |
| Observations, runs, forecasts, metrics | ❌ **never seeded** | Produced only from real CDC files by the pipeline |
| Demo capacity placeholders | Not in DB | `config/planning.toml`; labelled **DEMO PLACEHOLDER — not data** |
| Test fixtures | `tests/fixtures/` only | Tiny deterministic synthetic series, labelled **TEST-ONLY**; excluded from Docker image; never shown in UI |

---

## 7. API conventions

| Topic | Rule |
|---|---|
| Base path | `/api/v1` |
| Formats | JSON, UTF-8; dates `YYYY-MM-DD` (Saturday week-ending) |
| Methods | `GET` for E1–E7, `POST` for E8 only. Others → 405 |
| Headers | Security headers per TRD §9.2; `Cache-Control: no-store` |
| Request ID | `X-Request-ID` generated server-side; returned in headers and in error bodies |
| Unknown params | **Rejected** (422) |
| Body size | POST body > 8 KB → 413 |
| Rate limit | 429 + `Retry-After` (A-10) |

### 7.1 Error envelope (all non-2xx)

```json
{ "error": { "code": "validation_error", "message": "One or more inputs are invalid.",
             "fields": ["surge_pct"], "request_id": "…" } }
```

| HTTP | `code` | When |
|---|---|---|
| 404 | `series_unavailable` | Valid disease/jurisdiction but no current run (e.g., failed validation) |
| 405 | `method_not_allowed` | Wrong verb |
| 413 | `payload_too_large` | Body > 8 KB |
| 422 | `validation_error` | Bad/unknown/out-of-range input (field **names** only; input values are not echoed) |
| 429 | `rate_limited` | Limit exceeded |
| 500 | `internal_error` | Any unhandled exception (details only in server log) |
| 503 | `data_unavailable` | DB missing/unreadable or no data loaded |

### 7.2 Shared parameter validation

| Param | Type | Rule |
|---|---|---|
| `disease` | enum | `flu`, `covid19`, `rsv` (default `flu`) |
| `jurisdiction` | string | Must equal a code in T3 (MVP: only `US`); checked against the DB, not free-form |
| `horizon` | int | 1–4 |
| `from`, `to` | date | ISO date; `from ≤ to`; clamped to available range |
| `threshold` | number | Finite, `0 ≤ x ≤ 1e9` (🧪 sanity bound) |

---

## 8. Endpoint contracts

> `tier` ∈ `normal | watch | elevated`. All numbers below are **placeholders**.

### E1 — `GET /api/v1/health`
```json
{ "status": "ok", "db_ok": true, "data_as_of": "YYYY-MM-DD", "version": "0.1.0" }
```
503 `data_unavailable` if the DB cannot be read. Used by Docker `HEALTHCHECK`.

### E2 — `GET /api/v1/meta`  *(F8, F10, F12)*
```json
{
  "app": { "name": "CareCast", "version": "0.1.0", "env": "prod" },
  "data_as_of": "YYYY-MM-DD",
  "source": { "name": "…", "publisher": "CDC/NHSN", "dataset_id": "…", "url": "…",
              "retrieved_at": "…", "file_sha256": "…" },
  "diseases": [ { "code": "flu", "label": "Influenza", "available": true, "reason": null },
                { "code": "rsv", "label": "RSV", "available": false, "reason": "…" } ],
  "jurisdictions": [ { "code": "US", "name": "United States (national)", "level": "national" } ],
  "horizons": [1,2,3,4],
  "target_kind": { "flu": "count", "covid19": "count", "rsv": "count" },
  "defaults": {
    "threshold_method": "percentile_75_of_training_block",
    "interval_level": 0.8,
    "scenario": { "min": -50, "max": 100, "presets": [0,10,20] },
    "capacity": { "typical_weekly_admissions": 0, "alos_days": 0, "staffed_beds": 0, "patients_per_nurse": 0,
                  "is_simulated": true, "note": "DEMO PLACEHOLDERS — not data" }
  },
  "limitations": [ { "id": "L-01", "text": "…" } ],
  "quality_issues": [ { "check_name": "…", "severity": "warning", "detail": "…" } ],
  "disclaimer": "Demonstration forecasts. Not clinically validated. Decision support only."
}
```
Capacity numbers come from `config/planning.toml` (placeholders are chosen there in P4).

### E3 — `GET /api/v1/summary?disease=&jurisdiction=&threshold=`  *(F5, F9, F11)*
```json
{
  "data_as_of": "YYYY-MM-DD", "stale": false,
  "selected": {
    "disease": "flu", "jurisdiction": "US", "target_kind": "count", "unit": "admissions per week",
    "latest": { "week_end_date": "…", "value": 0, "change_pct_vs_prior_week": 0 },
    "threshold": { "value": 0, "source": "default" },
    "next_week": { "target_week_end_date": "…", "point": 0, "lower": 0, "upper": 0, "tier": "watch", "model_name": "linear_lag" },
    "ring": { "forecast_pct_of_threshold": 0, "lower_pct": 0, "upper_pct": 0 },
    "recent": [ { "week_end_date": "…", "value": 0 } ],
    "actions": { "tier": "watch", "items": ["…"], "footer": "Final decisions rest with authorised staff." }
  },
  "watchlist": [ { "disease": "flu", "label": "Influenza", "available": true,
                   "latest_value": 0, "next_week_point": 0, "tier": "normal", "threshold": 0 } ],
  "evaluation_headline": { "horizon_weeks": 1, "selected_model": "linear_lag",
                           "test_mae": 0, "persistence_test_mae": 0,
                           "beats_persistence": true, "test_interval_coverage": 0 }
}
```
- `recent` = last 8 observed weeks. `threshold` override applies **only** to `selected`; watchlist uses defaults.
- `ring.*_pct` = `point|lower|upper ÷ threshold × 100`. If threshold = 0 → fields are `null`.
- `stale` = `data_as_of` older than 2 reporting weeks vs. server date (A-11).

### E4 — `GET /api/v1/observations?disease=&jurisdiction=&from=&to=`  *(F2)*
```json
{ "disease": "flu", "jurisdiction": "US", "target_kind": "count", "unit": "admissions per week",
  "count": 0,
  "points": [ { "week_end_date": "…", "value": 0, "is_imputed": false, "pct_reporting": null } ] }
```
Ascending by date. Empty range → `count: 0, points: []` (200), not an error.

### E5 — `GET /api/v1/forecast?disease=&jurisdiction=&threshold=`  *(F3, F5, F9)*
```json
{
  "run": { "id": 0, "created_at": "…", "data_end_date": "…", "target_kind": "count" },
  "interval_level": 0.8,
  "threshold": { "value": 0, "source": "default", "method": "percentile_75_of_training_block" },
  "horizons": [
    { "horizon_weeks": 1, "origin_week_end_date": "…", "target_week_end_date": "…",
      "point": 0, "lower": 0, "upper": 0, "model_name": "linear_lag", "tier": "normal" }
  ],
  "actions": { "tier": "normal", "items": ["…"], "footer": "…" },
  "disclaimer": "Planning signal — not a bed-shortage prediction."
}
```
Always returns horizons 1–4 ascending (AT-09).

### E6 — `GET /api/v1/evaluation?disease=&jurisdiction=&horizon=1`  *(F4)*
```json
{
  "run": { "id": 0, "train": ["…","…"], "validation": ["…","…"], "test": ["…","…"],
           "n_train": 0, "n_valid": 0, "n_test": 0 },
  "metrics": [ { "horizon_weeks": 1, "model_name": "baseline_persistence", "split": "test",
                 "mae": 0, "rmse": 0, "n_eval": 0, "mae_vs_persistence": null, "is_selected": false } ],
  "selected": [ { "horizon_weeks": 1, "model_name": "linear_lag",
                  "beats_persistence": true, "test_interval_coverage": 0 } ],
  "verdicts": [ { "horizon_weeks": 1, "beats_persistence": true,
                  "text": "On the held-out test weeks, the selected model's MAE is lower than the persistence baseline's." } ],
  "backtest": { "horizon_weeks": 1,
                "points": [ { "target_week_end_date": "…", "actual": 0, "predicted_selected": 0, "predicted_persistence": 0 } ] }
}
```
`verdicts[].text` is generated **only** from the stored comparison (AT-14). When the model does not beat persistence the text says so plainly.

### E7 — `GET /api/v1/explain?disease=&jurisdiction=&horizon=1`  *(F6)*
```json
{
  "horizon_weeks": 1, "model_name": "linear_lag",
  "base_value": 0, "prediction": 0,
  "contributions": [ { "feature": "y_lag0", "label": "Admissions last week", "value": 0, "feature_value": 0 } ],
  "permutation_importance": [ { "feature": "y_lag0", "label": "Admissions last week", "value": 0 } ],
  "text": "…associated with…",
  "note": "These are model associations, not causes."
}
```
`contributions` is `null` when the selected model is `hgb_lag` (UI states why). Identity: `base_value + Σ value = prediction` (AT-18).

### E8 — `POST /api/v1/scenario`  *(F5, F7, F8, F9)*
Request:
```json
{ "disease": "flu", "jurisdiction": "US", "surge_pct": 20, "threshold": null,
  "capacity": { "typical_weekly_admissions": 0, "alos_days": 0, "staffed_beds": 0, "patients_per_nurse": 0 } }
```
Response:
```json
{
  "is_scenario": true, "label": "SCENARIO — not a prediction", "surge_pct": 20,
  "threshold": { "value": 0, "source": "default" },
  "horizons": [ { "horizon_weeks": 1, "target_week_end_date": "…",
                  "base":     { "point": 0, "lower": 0, "upper": 0, "tier": "normal" },
                  "scenario": { "point": 0, "lower": 0, "upper": 0, "tier": "watch" } } ],
  "capacity": {
    "is_simulated": true, "label": "SIMULATED — assumption-based", "reference_level": 0,
    "inputs": { "typical_weekly_admissions": 0, "alos_days": 0, "staffed_beds": 0, "patients_per_nurse": 0 },
    "horizons": [ { "horizon_weeks": 1, "relative_change": 0, "hospital_weekly_admissions": 0,
                    "est_occupied_beds": 0, "bed_gap": 0, "nurses_per_shift": 0 } ],
    "formulae": [ "relative_change = scenario_point / reference_level",
                  "hospital_weekly_admissions = typical_weekly_admissions × relative_change",
                  "est_occupied_beds = hospital_weekly_admissions × alos_days / 7",
                  "bed_gap = est_occupied_beds − staffed_beds",
                  "nurses_per_shift = est_occupied_beds / patients_per_nurse" ],
    "message": null
  },
  "actions": { "tier": "watch", "items": ["…"], "footer": "…" }
}
```
If `reference_level = 0`, capacity numbers are `null` and `message` explains why. `capacity: null` in the request ⇒ defaults from `planning.toml`.

#### E8 validation

| Field | Type | Rule |
|---|---|---|
| `surge_pct` | number | −50 ≤ x ≤ 100 (🧪 A-09) |
| `threshold` | number \| null | as §7.2 |
| `capacity.typical_weekly_admissions` | number | 0 < x ≤ 1,000,000 (🧪 sanity bounds) |
| `capacity.alos_days` | number | 0.5 ≤ x ≤ 60 |
| `capacity.staffed_beds` | number | 0 < x ≤ 100,000 |
| `capacity.patients_per_nurse` | number | 1 ≤ x ≤ 50 |
| (any other key) | — | **rejected** |

These bounds are **input-sanity limits**, not clinical rules.

---

## 9. Query patterns (all parameterised)

| Used by | Pattern (placeholders only; never string-built) |
|---|---|
| Resolve run | `SELECT * FROM v_current_runs WHERE jurisdiction_code = ? AND disease_code = ?` |
| E4 | `SELECT week_end_date, <target col> AS value, is_imputed, pct_reporting FROM weekly_observations WHERE jurisdiction_code = ? AND disease_code = ? AND week_end_date BETWEEN ? AND ? ORDER BY week_end_date` |
| E5 | `SELECT … FROM forecasts WHERE run_id = ? ORDER BY horizon_weeks` |
| E6 | `SELECT … FROM evaluation_metrics WHERE run_id = ?` · `SELECT … FROM backtest_predictions WHERE run_id = ? AND horizon_weeks = ? AND split = 'test' ORDER BY target_week_end_date` |
| E7 | `SELECT … FROM feature_contributions WHERE run_id = ? AND horizon_weeks = ?` |
| E2 | `SELECT … FROM dataset_sources ORDER BY retrieved_at DESC LIMIT 1` · `SELECT … FROM data_quality_issues WHERE source_id = ?` |

The *target column* (`admissions_count` vs `admissions_rate_per_100k`) is chosen from a **hard-coded allow-list** keyed by `run.target_kind`, never from user input. AT-05 statically forbids f-string/concatenated SQL.

---

## 10. Config file shapes

`config/dataset_mapping.toml` (filled in P2)
```toml
[source]
dataset_id = ""            # ⚠️ TO-VERIFY
date_column = ""           # ⚠️ TO-VERIFY
jurisdiction_column = ""   # ⚠️ TO-VERIFY
[jurisdictions]            # CSV value -> canonical code
# "<csv national value>" = "US"
[diseases.flu]
count_column = ""          # preferred target
rate_column = ""           # fallback
level_column = ""
reporting_hospitals_column = ""
pct_reporting_column = ""
# repeat for [diseases.covid19], [diseases.rsv]
```

`config/planning.toml`
```toml
[capacity_defaults]        # DEMO PLACEHOLDERS — not data (A-08); chosen in P4 and labelled
typical_weekly_admissions = 0
alos_days = 0
staffed_beds = 0
patients_per_nurse = 0
reference_weeks = 4
[bounds]
surge_pct = [-50, 100]
[actions.normal]
items = ["…"]
[actions.watch]
items = ["…"]
[actions.elevated]
items = ["…"]
[limitations]              # L-01 … L-12, text copied verbatim from PRD §9
L-01 = "…"
[disclaimer]
text = "Demonstration forecasts. Not clinically validated. Decision support only."
```
(Zeros above are **syntax placeholders**; P4 sets and labels the real demo values.)

---

## 11. Schema-level privacy check (AT-45)
Test inspects `sqlite_master`: no column name matches `patient|name_of_person|dob|birth|ssn|mrn|address|phone|email`; tables contain only aggregate series and model artefacts.
