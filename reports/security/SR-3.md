# Incremental Security Review 3 (SR-3) — Phase 4

**Date / Time:** 13 Oct 2026  
**Scope:** Phase 4 Backend API & Planning Logic (`carecast/planning.py`, `carecast/api/main.py`, `carecast/api/routes.py`, `carecast/api/schemas.py`, `carecast/api/ratelimit.py`, `config/planning.toml`, `tests/api/test_api_endpoints.py`, `tests/api/test_api_security.py`, `tests/unit/test_planning.py`, `tests/contract/openapi.snapshot.json`, `tests/contract/test_openapi_contract.py`)  
**Target:** Phase 4 Backend API, Security Middleware, Planning Logic & Contract Snapshot  
**Review Type:** Incremental Review (Master Prompt #1 / TRD §9.3 INC-01...INC-10)

---

## 1. Security Checklist (INC-01 – INC-10)

| Control | Applicability & Rationale | Status | Findings | Fix / Mitigation | Evidence |
|---|---|---|---|---|---|
| **INC-01 Permission checks** | **NOT APPLICABLE** (D-04). Public aggregate data; no user accounts or authenticated resources exist. All endpoints E1–E7 are read-only GET; E8 is a stateless POST computation. | **N/A** | Verified that no endpoint writes data to SQLite. DB connection opened with `connect_ro()` (`mode=ro` and `PRAGMA query_only = ON`). | Write attempts rejected by SQLite engine. | `test_api_security.py::TestReadOnlyDBConnectionFailsWrites` PASSED. |
| **INC-02 Secrets, API keys, tokens** | **APPLICABLE**. API routes, configuration, schemas, and planning logic must contain zero embedded credentials, API tokens, or keys. | **PASS** | None. Secret scan returned clean. | None required. | `git grep -nEi "(api[_-]?key\|secret\|token...)"` clean. |
| **INC-03 User input validation** | **APPLICABLE**. All query parameters and JSON payloads must be strictly validated against bounds and reference schemas. | **PASS** | Pydantic v2 schemas configured with `ConfigDict(extra="forbid")`. Numeric inputs bounded: `surge_pct` $\in [-50, 100]$, `threshold` $\in [0, 10^9]$, capacity bounds strictly checked. Enums (`disease`, `jurisdiction`) validated against SQLite tables. Date ranges checked (`from <= to`). | Unmapped or extra fields rejected with HTTP 422. Out-of-bounds numbers rejected. | `test_api_endpoints.py::TestThresholdInputSanityAT16`, `TestScenarioE8AT22AT25`, `test_api_security.py::TestUnknownFieldsForbidden` PASSED. |
| **INC-04 Safe error messages** | **APPLICABLE**. Errors must provide generic, non-disclosing envelopes without leaking stack traces, database schemas, or filesystem paths. | **PASS** | Custom exception handlers for `RequestValidationError`, `StarletteHTTPException`, and generic `Exception`. Validation errors report field names only; 500 errors return `"An internal server error occurred."` with zero stack or query disclosure. | Handled via structured `ErrorResponse` envelope (`BACKEND_SCHEMA §7.1`). | `test_api_security.py::TestForcedServerErrorAT34` PASSED. |
| **INC-05 UGC sanitisation** | **APPLICABLE (light)**. No user-generated content stored or persisted. User inputs are numbers and canonical codes. | **PASS** | No string content stored or reflected back in raw HTML. API responses are pure JSON with strict schema typing. | None required. | All endpoints return typed JSON models. |
| **INC-06 Parameterised SQL** | **APPLICABLE**. All SQLite queries in `carecast/api/routes.py` must use parameterised placeholders (`?`). Target column names must be chosen from a safe allowlist. | **PASS** | All queries use literal SQL string constants with `?` parameters. Target columns selected exclusively from `TARGET_ALLOWLIST = {"count": "admissions_count", "rate": "admissions_rate_per_100k"}`. Zero f-strings or format operations. | Verified by AST static analysis guard. | `test_sql_guard.py::test_at_05_sql_guard_no_dynamic_queries` PASSED. |
| **INC-07 File uploads** | **NOT APPLICABLE**. No file upload handlers or multipart routes exist in CareCast. | **N/A** | None. `python-multipart` is not installed; no upload endpoints exposed. | N/A | No multipart route exists. |
| **INC-08 Rate limiting** | **APPLICABLE**. Endpoints must be protected against abusive request bursts and denial of service. | **PASS** | Implemented `SlidingWindowRateLimiter` with thread-safe sliding window tracking. Configured via `CARECAST_RATE_GET_PER_MIN` (60) and `CARECAST_RATE_POST_PER_MIN` (20). Rate limit breach returns HTTP 429 with `Retry-After` header. | Rate limiting middleware active across `/api/*`. | `test_api_security.py::TestRateLimiterAT35` PASSED. |
| **INC-09 CSRF** | **NOT APPLICABLE**. No session cookies or browser credentials exist. | **N/A** | Verified that no cookies are used or set (`Set-Cookie` header absent). Verified that CORS middleware is absent (`Access-Control-Allow-*` absent). | Strict header scrubbing in security middleware. | `test_api_security.py::TestNoCorsAndNoCookiesAT37` PASSED. |
| **INC-10 Sensitive data exposure** | **APPLICABLE (light)**. Responses must omit internal paths, debug information, or patient-level data. | **PASS** | Schema contains only aggregated counts/rates. In production mode (`CARECAST_ENV=prod`), `/docs`, `/redoc`, and `/openapi.json` are disabled and return 404. All API responses include `Cache-Control: no-store`. | Strict security response headers enforced (CSP, X-Content-Type-Options, Referrer-Policy, X-Frame-Options: DENY, Permissions-Policy). | `test_api_security.py::TestSecurityHeadersAT33`, `TestDocsDisabledInProd` PASSED. |

---

## 2. Automated Security Scans

### A. Bandit Security Linter
- **Command:** `python -m bandit -r carecast -s B404`
- **Output:** Clean exit (code 0). 0 issues identified across 3,471 lines of code.

### B. Secret Scan
- **Command:** `git grep -nEi "(api[_-]?key|secret|token|passwd|password|bearer|private[_-]?key)" -- . ":(exclude)docs" ":(exclude)reports" ":(exclude)*.json"`
- **Output:** Clean — 0 secrets found.

### C. SQL Injection AST Guard (AT-05)
- **Command:** `pytest -v tests/unit/test_sql_guard.py`
- **Output:** PASSED — Verified that no dynamic SQL queries exist in `carecast/api/routes.py` or anywhere in `carecast/`.

---

## 3. What Was Changed and Why
- Implemented `SecurityAndHardeningMiddleware` in `carecast/api/main.py`:
  - Enforces mandatory security headers on every response: CSP (`frame-ancestors 'none'`), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, and `Cache-Control: no-store` on API routes.
  - Automatically generates server-side UUID4 `X-Request-ID` and injects it into headers and error responses.
  - Hardened POST body limit to 8 KB (`MAX_BODY_BYTES = 8192`), rejecting oversized payloads with HTTP 413.
  - Added in-memory sliding-window rate limiter per client IP.
  - Strips any CORS or Cookie headers to guarantee same-origin and cookie-free operation.
- Implemented read-only database isolation in `carecast/api/routes.py`:
  - Enforces `connect_ro()` with `mode=ro` and `PRAGMA query_only = ON`. Write attempts from API handlers fail with SQLite operational errors.
- Hardened input schemas with `ConfigDict(extra="forbid")` in `carecast/api/schemas.py`:
  - Any unknown query parameters or JSON body fields are strictly rejected with HTTP 422 `validation_error`.
- Configured documentation exposure control:
  - `/docs`, `/redoc`, and `/openapi.json` are completely disabled unless `CARECAST_ENV=dev` and `CARECAST_ENABLE_DOCS=1`.

---

## 4. Residual Risks
- Public rate limiting uses in-memory tracking per process; in multi-worker production setups behind a load balancer, distributed rate limiting (e.g., Redis or reverse proxy) would be required if scaled horizontally. For single-process SQLite deployments, in-memory sliding window provides sufficient DoS protection.
- All numbers returned are decision support signals based on CDC historical surveillance and are explicitly not clinical forecasts (governed by disclaimers on E2, E3, E5, E8).
