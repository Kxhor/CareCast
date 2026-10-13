# Pre-Launch Security Review (PL) — CareCast

**Date:** 2026-10-14  
**Auditor:** ML Auditor & Security Specialist (Rule G-0 Protocol)  
**Scope:** Complete Codebase, Configuration, and Local Deployment Package  
**Reference:** `ANTIGRAVITY_PROMPTS.md` §6.3, `TRD.md` §9.3 (PL-01 – PL-13), Master Security Prompt #2  
**Verdict:** **PASSED — ALL APPLICABLE CONTROLS SATISFIED**

---

## 1. Pre-Launch Review Checklist (PL-01 – PL-13)

| ID | Master Item Description | CareCast Applicability & Decision | Status | Verification Command & Raw Evidence |
|---|---|---|---|---|
| **PL-01** | All secrets are in environment variables, not in code | **APPLICABLE**. System requires no API keys or third-party cloud secrets. Settings loaded from environment or TOML defaults. | **PASS** | `git grep -nEi "(api[_-]?key\|secret\|token\|passwd\|password\|bearer\|private[_-]?key)" -- . ":(exclude)docs" ":(exclude)reports"`<br>Found only explanatory comments in `.env.example`, `carecast/settings.py:5`, and test assertions in `tests/unit/test_schema_constraints.py`. Git history clean. |
| **PL-02** | All user input is validated on the backend | **APPLICABLE**. Strict Pydantic models with `model_config = ConfigDict(extra="forbid")` on all inputs. Enums checked against DB allow-lists. Query parameters clamped to non-negative floats. Body capped at 8 KB. | **PASS** | `pytest tests/api/test_api_endpoints.py tests/api/test_api_security.py`<br>Passed. Node IDs `TestUnknownFieldsForbidden::test_extra_field_rejected` (422) and `TestBodySizeLimit::test_large_body_returns_413` (413) verify backend rejection of malformed or oversized input. |
| **PL-03** | All database queries use parameterised queries | **APPLICABLE**. All SQL statements in `carecast/api/routes.py`, `carecast/storage.py`, and `carecast/ingest.py` use `?` placeholders. Target column selection uses hard-coded allow-list. DB connection is read-only (`?mode=ro`, `PRAGMA query_only = ON`). | **PASS** | `pytest tests/unit/test_sql_guard.py -v`<br>Passed AT-05 (`test_at_05_sql_guard_no_dynamic_queries` PASSED in 0.05s). AST parser verified 0 string formatting or concatenation in SQLite query executions. |
| **PL-04** | All API endpoints have authentication and authorization checks | **NOT APPLICABLE** per CareCast Architectural Decision D-04. Public health surveillance dashboard; all endpoints are read-only public aggregations. Scenario computation (E8) is purely functional and stateless. | **N/A** | Verified `carecast/api/routes.py`: zero user accounts, zero write endpoints, zero session state. Database is mounted read-only. |
| **PL-05** | Error messages don't expose internal details | **APPLICABLE**. Exception middleware catches unhandled errors and renders generic JSON envelope (`{"error": {"code": "...", "message": "...", "request_id": "..."}}`). | **PASS** | `pytest tests/api/test_api_security.py -k test_forced_error_envelope`<br>Passed AT-34 (`TestForcedServerErrorAT34::test_forced_error_envelope` PASSED). Server path, Python traceback, and database exceptions are completely suppressed in responses. |
| **PL-06** | CORS is locked to my domain only | **APPLICABLE**. Static SPA and API are served same-origin via FastAPI static mount. Zero CORS middleware registered. Any `Access-Control-*` headers are stripped in middleware. | **PASS** | `pytest tests/api/test_api_security.py -k test_no_cors_and_no_cookies`<br>Passed AT-37 (`TestNoCorsAndNoCookiesAT37::test_no_cors_and_no_cookies` PASSED). Confirmed 0 `Access-Control-*` headers emitted. |
| **PL-07** | Debug mode is off | **APPLICABLE**. In production (`CARECAST_ENV=prod`), OpenAPI schemas, Swagger UI (`/docs`), and ReDoc (`/redoc`) return 404 Not Found. Auto-reload disabled. | **PASS** | `pytest tests/api/test_api_security.py -k test_docs_404_in_prod`<br>Passed AT-36 (`TestDocsDisabledInProd::test_docs_404_in_prod` PASSED). Verified `/docs`, `/redoc`, and `/openapi.json` return HTTP 404 Not Found in prod mode. |
| **PL-08** | All cookies have secure, httpOnly and sameSite flags | **NOT APPLICABLE**. CareCast uses zero session cookies and zero persistent browser state. Middleware explicitly strips any `Set-Cookie` header. | **N/A** | `pytest tests/api/test_api_security.py -k test_no_cors_and_no_cookies`<br>Passed AT-37. Verified zero `Set-Cookie` headers present on all responses. |
| **PL-09** | HTTPS is enforced everywhere | **NOT APPLICABLE** for local HTTP demo deployment (OD-04 Option B). For production reverse proxy deployment, `CARECAST_HSTS=1` activates `Strict-Transport-Security: max-age=31536000; includeSubDomains`. | **N/A (Local) / PASS (Config)** | Local deployment runs over loopback HTTP (`127.0.0.1:8000`). Production proxy configuration documented in `docs/DEPLOYMENT.md`. HSTS header logic verified via `TestSecurityHeadersAT33::test_hsts_header_when_enabled`. |
| **PL-10** | Rate limiting is in place on login and sensitive endpoints | **APPLICABLE** (partial). No login exists. In-memory sliding-window limiter protects GET endpoints (default 60/min) and computation endpoint E8 (default 20/min). | **PASS** | `pytest tests/api/test_api_security.py -k "rate_limit"`<br>Passed AT-35 (`test_rate_limit_exceeded` and `test_at_35_post_scenario_rate_limit` PASSED). Burst traffic triggers HTTP 429 Too Many Requests with `Retry-After: 60`. |
| **PL-11** | File uploads are validated and stored securely | **NOT APPLICABLE**. Zero file upload endpoints exist in CareCast. Raw CDC data is ingested offline via CLI orchestrator. | **N/A** | Verified route definitions: 0 `multipart/form-data` endpoints. `grep -in "multipart"` returned 0 matches across requirements and API codebase. |
| **PL-12** | Dependencies have no known critical vulnerabilities | **APPLICABLE**. Automated vulnerability scan of all Python and JavaScript packages. | **PASS** | `python -m pip_audit`<br>Output: `No known vulnerabilities found`. Vendored Chart.js v4.4.7 verified against npm advisory database (SHA-256 `8f070cb70bb8dd076cfb819f72db7b5ae15a319409ce818c322b64ffaf7e6714`, 0 CVEs). |
| **PL-13** | No test credentials, dummy data or development artifacts remain | **APPLICABLE**. Production database contains only authentic CDC NHSN data. Test fixtures isolated in `tests/`. Demo capacity parameters explicitly labeled. | **PASS** | Verified `config/planning.toml:12`: `note = "DEMO PLACEHOLDER — not data"`. `.gitignore` verified to exclude `.venv/`, `.env`, `GeminiSetup.exe`, `Reference_Ui.jpg`, `logs_utf16_bak/`. |

---

## 2. Security Findings & Fixes Summary

- **Vulnerabilities Found:** 0
- **Remediations Required:** 0
- **Residual Risks:**
  - *In-Memory Rate Limiting:* The current rate limiter resides in application memory and resets on process restart. Acceptable for single-instance virtualenv deployment per OD-04. A distributed cache (e.g., Redis) should be introduced if horizontal scaling is pursued in future releases.
  - *Local HTTP:* Local virtualenv deployment operates over plaintext HTTP on localhost. Production deployments must place CareCast behind a TLS-terminating reverse proxy (Nginx, Caddy, or Cloud Run load balancer) with `CARECAST_HSTS=1`.
