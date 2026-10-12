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
