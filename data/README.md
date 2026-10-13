# Data Provenance and Storage

This directory holds project data artifacts:
- `raw/`: Unmodified CDC source datasets (CSV format, git-ignored).
- `carecast.db`: SQLite database built by `python -m carecast.pipeline` (git-ignored).

### Source Data Acquisition

The dataset is publicly hosted by the Centers for Disease Control and Prevention (CDC) National Healthcare Safety Network (NHSN):
- **Dataset Title:** Weekly Hospital Respiratory Data (HRD) Metrics by Jurisdiction
- **Dataset Identifier:** `ua7e-t2fy`
- **Download URL:** `https://data.cdc.gov/api/views/ua7e-t2fy/rows.csv?accessType=DOWNLOAD`
- **License:** Public Domain (attribution requested)

To acquire the dataset:
```bash
# Option 1: Automated rebuild (automatically downloads if not present)
python -m carecast.pipeline rebuild

# Option 2: Acquisition script
python scripts/download_data.py

# Option 3: Manual curl command
curl -o data/raw/ua7e-t2fy.csv "https://data.cdc.gov/api/views/ua7e-t2fy/rows.csv?accessType=DOWNLOAD"
```

See documentation in `docs/` for column mappings, schema definitions, and ingestion quality rules.
