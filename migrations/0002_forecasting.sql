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
