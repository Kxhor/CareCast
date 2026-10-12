# CareCast

> **Explainable Respiratory-Admission Forecasting and Capacity Early-Warning**  
> *College project · Decision support only · NOT clinically validated.*

---

## 1. Project Overview

CareCast is a transparent, explainable decision-support application designed to forecast weekly respiratory admissions (COVID-19, Influenza, RSV) at the national level using open CDC datasets. It provides capacity early-warning illustrations, surge scenario exploration, and plain-language attribution without black-box opacity.

Specifications and documentation are maintained in the [`docs/`](docs/) directory:
- [PRD.md](docs/PRD.md): Product Requirements Document
- [TRD.md](docs/TRD.md): Technical Requirements Document
- [APP_FLOW.md](docs/APP_FLOW.md): Application & State Flow
- [UI_UX_DESIGN.md](docs/UI_UX_DESIGN.md): Design System & Visual Specification
- [BACKEND_SCHEMA.md](docs/BACKEND_SCHEMA.md): Database Schemas & API Contracts
- [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md): Seven-Phase Implementation Plan
- [ANTIGRAVITY_PROMPTS.md](docs/ANTIGRAVITY_PROMPTS.md): Execution Prompts & Recovery Workflows
- [FINAL_PROJECT_AUDIT.md](docs/FINAL_PROJECT_AUDIT.md): Traceability & Final Audit

---

## 2. Setup & Environment

Requires **Python ≥ 3.11** (uses stdlib `tomllib`).

```bash
# Clone and enter directory
cd CareCast

# Create virtual environment and activate
python3 -m venv .venv
source .venv/bin/activate

# Install development dependencies
pip install -r requirements-dev.txt
```

---

## 3. Canonical Verification & Operations Commands (TRD §12)

```bash
# 1. Setup dependencies
pip install -r requirements-dev.txt

# 2. Data + Model Pipeline (offline)
python -m carecast.pipeline rebuild       # migrate -> ingest -> train
python -m carecast.pipeline check         # data-quality report

# 3. Development Server
CARECAST_ENV=dev python -m uvicorn carecast.api.main:app --host 127.0.0.1 --port 8000

# 4. Test Suites
python -m pytest -q                       # unit & API test suites
python -m pytest tests/e2e -q             # Playwright E2E browser tests

# 5. Full Verification Audit (AT-44)
python scripts/verify.py                  # Full test suite + pip-audit vulnerability scan

# 6. Screenshot Capture (Phase 6)
python scripts/capture_screenshots.py     # Captures responsive viewports into reports/screenshots/
```

---

## 4. Configuration

Default configuration is defined in `carecast/settings.py` and configurable via environment variables (`.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `CARECAST_ENV` | `prod` | `dev` enables reload helpers and optional docs; `prod` disables them |
| `CARECAST_DB_PATH` | `data/carecast.db` | SQLite database path (must be outside `web/`) |
| `CARECAST_ENABLE_DOCS` | `0` | Interactive Swagger/ReDoc docs (honoured only when `CARECAST_ENV=dev`) |
| `CARECAST_RATE_GET_PER_MIN` | `60` | Sliding-window GET rate limit per IP |
| `CARECAST_RATE_POST_PER_MIN` | `20` | Sliding-window POST rate limit per IP |
| `CARECAST_TRUSTED_PROXY` | `0` | Trust `X-Forwarded-For` header behind reverse proxies |
| `CARECAST_HSTS` | `0` | Enable HTTP Strict Transport Security header over HTTPS |
| `CARECAST_LOG_LEVEL` | `INFO` | Standard logging verbosity |

---

## 5. Security & Quality Guardrails

- **Zero Mock Substitution:** Real data and mathematical models only.
- **Leak-Free ML:** Chronological walk-forward splits; never shuffle time-series data.
- **Honest Metrics:** Always compared directly to the persistence baseline.
- **Explicit Labelling:** All synthetic or simulated scenario content is explicitly flagged `SIMULATED / SCENARIO`.
- **Read-Only SQLite Enforcement:** API queries use `mode=ro` with `PRAGMA query_only = ON`.
