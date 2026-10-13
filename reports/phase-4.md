# Phase 4 Report — Backend API & Planning Logic

**Date / Time:** 13 Oct 2026  
**Status:** COMPLETE — Ready for Gate Review (`APPROVED: PHASE 4`)  
**Operating Rules Followed:** G-0, BACKEND_SCHEMA §7–§10, TRD §4, §6, §9, PRD F5, F7–F10, Acceptance Tests Catalog  

---

## 1. Executive Summary & Verification Evidence

Phase 4 delivers the hardened, read-only REST API (endpoints E1 through E8), pure domain planning functions, and HTTP security infrastructure for CareCast:

- **Pure Planning Engine (`carecast/planning.py`):**
  - Alert tier evaluation (`calculate_tier` per PRD F5.2 / AT-15): Evaluates thresholds against point/lower/upper intervals yielding `normal`, `watch`, or `elevated`.
  - What-if scenario analysis (`calculate_scenario` per PRD F7.1 / AT-21): Evaluates percentage surge scalings in $[-50, +100]\%$.
  - Steady-state capacity illustration (`calculate_capacity_illustration` per PRD F8.2 / AT-24): Computes Little's law approximations (occupied beds, bed gap, nurses per shift); safely handles `reference_level = 0`.
  - Static tier action checklists (`get_action_checklist` per PRD F9.1-F9.2 / AT-26): Fixed, deterministic checklists with mandatory non-clinical governance footer.
  - Non-causal explanation formatting (`format_explanation_text` per PRD F6.3 / AT-19): Produces templated explanations using "associated with" terminology; zero causal verbs.
- **Planning & Policy Configuration (`config/planning.toml`):**
  - Realistic capacity placeholders clearly labelled `DEMO PLACEHOLDER — not data` (PRD F8.1, Rule A-08).
  - Verbatim limitations L-01 through L-12 copied from PRD §9.
  - Standard disclaimer and input-sanity bounds.
- **REST API Endpoints E1–E8 (`carecast/api/routes.py`, `schemas.py`):**
  - E1: `GET /api/v1/health` — liveness, DB status, data-as-of, app version.
  - E2: `GET /api/v1/meta` — provenance, datasets, available diseases, jurisdictions, defaults, limitations, and data quality issues.
  - E3: `GET /api/v1/summary` — overview widgets for selected disease, next-week forecast, tier, ring gauge, recent 8 weeks, watchlist, and evaluation headline.
  - E4: `GET /api/v1/observations` — historical observation series filtered by date range ascending.
  - E5: `GET /api/v1/forecast` — horizons 1–4 ascending, empirical intervals, tiers, and actions.
  - E6: `GET /api/v1/evaluation` — partition splits, model metrics, selected models, verdicts, and backtest points.
  - E7: `GET /api/v1/explain` — linear additive contributions (or null for trees), permutation importances, non-causal explanation text.
  - E8: `POST /api/v1/scenario` — stateless what-if surge simulation and capacity illustration.
- **Pydantic Schemas (`carecast/api/schemas.py`):**
  - All models configured with `ConfigDict(extra="forbid")` rejecting unknown parameters.
  - Enums and parameters validated against the active SQLite reference tables.
- **Security & HTTP Hardening (`carecast/api/main.py`, `ratelimit.py`):**
  - Security headers on all responses: CSP (`default-src 'self'`, `frame-ancestors 'none'`), `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, `Permissions-Policy`, and `Cache-Control: no-store` on API routes.
  - Strict absence of CORS middleware and Cookies (`Set-Cookie` and `Access-Control-*` scrubbed).
  - Server-side generated `X-Request-ID` UUID on all requests and error envelopes.
  - 8 KB body size limit on POST requests (`MAX_BODY_BYTES = 8192` -> HTTP 413).
  - Thread-safe in-memory sliding-window rate limiter per client IP.
  - Documentation routes (`/docs`, `/redoc`, `/openapi.json`) disabled in production mode.
  - Read-only database connection isolation (`connect_ro`, `mode=ro`, `PRAGMA query_only = ON`).
  - Static mount for `web/` with a placeholder `index.html`.
- **OpenAPI Contract Snapshot (`tests/contract/openapi.snapshot.json`):**
  - Dumped from `app.openapi()` and verified by automated regression test `test_openapi_contract.py` (AT-47).

---

## 2. Acceptance Test Verification Matrix

| Acceptance Test | Requirement | Description / Pass Condition | Result | Evidence File / Test Name |
|---|---|---|:---:|---|
| **AT-06** | F2 | `GET /observations` returns ascending dates; `from > to` returns 422; filters bound results. | **PASS** | `tests/api/test_api_endpoints.py::TestObservationsE4AT06` |
| **AT-09** | F3 | `GET /forecast` returns 4 horizons ascending; `lower <= point <= upper`; target date = origin + $7 \cdot h$ days. | **PASS** | `tests/api/test_api_endpoints.py::TestForecastE5AT09` |
| **AT-10 (API)** | F3/F4 | Empirical coverage on test block is exposed in API evaluation responses. | **PASS** | `tests/api/test_api_endpoints.py::TestEvaluationE6AT10` |
| **AT-15** | F5 | Boundary table: `point == threshold` -> Watch (if upper > threshold); `point > threshold` -> Elevated; `upper == threshold` -> Normal. | **PASS** | `tests/unit/test_planning.py::TestTierBoundaryTableAT15` |
| **AT-16** | F5 | Non-numeric, negative, NaN/inf, > bound threshold query returns 422. | **PASS** | `tests/api/test_api_endpoints.py::TestThresholdInputSanityAT16` |
| **AT-19** | F6 | Explanation text produced from stored numbers; contains zero causal terms (list-based test). | **PASS** | `tests/unit/test_planning.py::TestExplanationNonCausalLanguageAT19` |
| **AT-21** | F7 | `adjusted = base * (1 + pct / 100)` for point/lower/upper; `pct = 0` equals base. | **PASS** | `tests/unit/test_planning.py::TestScenarioScalingAT21` |
| **AT-22** | F7 | `surge_pct` outside $[-50, 100]$ returns 422. | **PASS** | `tests/api/test_api_endpoints.py::TestScenarioE8AT22AT25` |
| **AT-24** | F8 | Worked example (typical 100/wk, relative_change 1.2, ALOS 5, ratio 6) yields formula results exactly; reference_level = 0 handled. | **PASS** | `tests/unit/test_planning.py::TestCapacityIllustrationAT24` |
| **AT-25 (API)** | F8 | `is_simulated = true` returned in API response; capacity clearly labelled. | **PASS** | `tests/api/test_api_endpoints.py::TestScenarioE8AT22AT25` |
| **AT-26** | F9 | Each tier returns a fixed, deterministic checklist ending with standard non-clinical footer. | **PASS** | `tests/unit/test_planning.py::TestActionChecklistAT26` |
| **AT-28** | F10 | `GET /meta` returns provenance, dataset ID, SHA-256, data-as-of, disclaimers, and L-01 to L-12. | **PASS** | `tests/api/test_api_endpoints.py::TestMetaE2AT28` |
| **AT-30** | F11 | `GET /summary` returns latest, next-week forecast, tier, ring gauge, and watchlist for each available disease. | **PASS** | `tests/api/test_api_endpoints.py::TestSummaryE3AT30` |
| **AT-33** | N1 | CSP, `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options` present on all responses. | **PASS** | `tests/api/test_api_security.py::TestSecurityHeadersAT33` |
| **AT-34** | N1 | Forced server error returns generic JSON envelope; no traceback, path, or SQL leaked. | **PASS** | `tests/api/test_api_security.py::TestForcedServerErrorAT34` |
| **AT-35** | N1 | Exceeding rate limit returns HTTP 429 with `Retry-After` header. | **PASS** | `tests/api/test_api_security.py::TestRateLimiterAT35` |
| **AT-37** | N1 | Zero `Access-Control-Allow-*` and zero `Set-Cookie` in any response. | **PASS** | `tests/api/test_api_security.py::TestNoCorsAndNoCookiesAT37` |
| **API Read-Only** | TRD §9.1 | Write operation through the API connection strictly fails with SQLite operational error. | **PASS** | `tests/api/test_api_security.py::TestReadOnlyDBConnectionFailsWrites` |
| **AT-47 (P4)** | N1 | OpenAPI specification contract snapshot matches current `app.openapi()`. | **PASS** | `tests/contract/test_openapi_contract.py` |

---

## 3. Test Suite & Verification Results

- **Command:** `pytest -v`
- **Output:** **99 passed, 0 failures, 17 warnings** in 10.14 seconds.
- **Log:** `reports/logs/p4-pytest.txt`
- **Breakdown:**
  - `tests/api/`: 35 passed
  - `tests/contract/`: 1 passed
  - `tests/unit/`: 63 passed

---

## 4. Live curl Verification Against Real Database

All endpoints were called with live `curl.exe` against `127.0.0.1:8000` connected to `data/carecast.db`:
- **Log:** `reports/logs/p4-curl-endpoints.txt`
- **Verified Calls:**
  - `E1_HEALTH`: HTTP 200 (`status="ok"`, `db_ok=true`, `data_as_of="2026-10-03"`, `version="0.1.0"`).
  - `E2_META`: HTTP 200 (real NHSN dataset metadata, SHA-256 `cdbde5be...`, L-01 to L-12, capacity defaults).
  - `E3_SUMMARY_FLU`: HTTP 200 (`latest=3334.0`, `next_week=4222.7`, `tier="normal"`, `threshold=10828.25`, watchlist with Flu, COVID-19, RSV).
  - `E3_SUMMARY_COVID`: HTTP 200 (`latest=4253.0`, `next_week=3853.0`, `tier="normal"`, `threshold=15743.0`).
  - `E3_SUMMARY_RSV`: HTTP 200 (`latest=541.0`, `next_week=937.2`, `tier="normal"`, `threshold=5287.0`).
  - `E4_OBSERVATIONS`: HTTP 200 (13 weekly points between `2024-01-06` and `2024-03-30`).
  - `E5_FORECAST_FLU`: HTTP 200 (4 horizons ascending, empirical lower/upper bounds, action checklist).
  - `E6_EVALUATION_FLU_H1`: HTTP 200 (split sizes 94/31/33, test MAE 595.73 vs persistence 564.76, 33 backtest points).
  - `E7_EXPLAIN_FLU_H1`: HTTP 200 (`base_value=7327.22`, linear contributions summing to prediction `4222.72`, permutation importances, non-causal explanation text).
  - `E8_SCENARIO_FLU`: HTTP 200 (20% surge scaled forecast, simulated capacity bed gap and nurse requirements).
  - `ERROR_422_VALIDATION`: HTTP 422 with structured envelope (`fields: ["from", "to"]`).
  - `ERROR_413_PAYLOAD_TOO_LARGE`: HTTP 413 (`code="payload_too_large"`, `request_id`).

---

## 5. Incremental Security Review (SR-3) Summary

Full 10-item review documented in `reports/security/SR-3.md`:
- **Bandit Linter:** 0 security issues identified across 3,471 lines of code (`python -m bandit -r carecast -s B404`).
- **Secret Scan:** Clean — 0 hardcoded secrets.
- **SQL Injection Guard (AT-05):** Clean — 100% parameterised SQL with static strings and column allowlist.
- **Permissions & Database Access:** Read-only SQLite connection strictly enforced.

---

## 6. Phase 4 Gate Checklist

```
[x] Docs read and listed          [x] Repo state reported before changes
[x] Only this phase's scope built [x] No new dependency (or approval requested)
[x] Every AT for this phase run   [x] Raw outputs saved in reports/logs/
[x] Failures documented + fixed   [x] Security review done (SR-3) or N/A stated
[x] No fabricated numbers         [x] Deviations listed (none)
[x] STOPPED and waiting for "APPROVED: PHASE 4"
```
