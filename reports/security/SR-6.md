# Incremental Security Review 6 (SR-6) — Phase 7 Closure & Post-Phase-3 Delta

**Date / Time:** 2026-10-14  
**Scope (`git diff --stat phase-3-approved -- carecast web tests config`):**
```text
 carecast/api/main.py      |  313 +++++++++++-
 carecast/api/ratelimit.py |   54 +-
 carecast/api/routes.py    | 1227 ++++++++++++++++++++++++++++++++++++++++++++-
 carecast/api/schemas.py   |  452 ++++++++++++++++-
 carecast/db.py            |    2 +-
 carecast/planning.py      |  198 +++++++-
 6 files changed, 2240 insertions(+), 6 deletions(-)
```
*(Note: untracked files `web/`, `config/planning.toml`, and tests added in Phases 4–7 were also reviewed alongside tracked deltas).*  
**Review Type:** Incremental Review (Master Prompt #1 / TRD §9.3 INC-01…INC-10)  
**Status:** REVISED — PENDING USER REVIEW

---

## 1. Security Checklist (INC-01 … INC-10)

| Control | Applicability & Rationale | Status | Findings | Fix / Mitigation | Evidence |
|---|---|---|---|---|---|
| **INC-01 Permission checks** | **NOT APPLICABLE** (D-04). Public aggregated respiratory surveillance dashboard. No authentication, authorization, or user accounts. | **N/A** | All endpoints E1–E7 are read-only public GET endpoints. E8 (`/api/v1/scenario`) is purely computational and stateless. No user accounts or sessions exist. | None required (verified stateless). | `git grep -n "def " carecast/api/routes.py` confirms no authenticated or state-mutating endpoints. |
| **INC-02 Hard-coded secrets** | **APPLICABLE**. Codebase, configs, client bundles, and scripts must contain zero API keys, secrets, or credentials. | **PASS** | Automated scan over `carecast`, `web`, `config`, `scripts` identified only 2 non-secret occurrences: `carecast/settings.py:5` (docstring comment) and `web/index.html:9-10` (CSS "design tokens" reference); both classified as **FALSE POSITIVES**. Zero keys or passwords found. | None required. | `git grep -rIlE "(api[_-]?key\|secret\|token\|passwd)"` clean. |
| **INC-03 Backend input validation** | **APPLICABLE**. Strict validation on all incoming query and body parameters. | **PASS** | Pydantic schemas enforce `extra="forbid"`. Bounds and disease/target allowlists strictly verified on backend. Body size capped at 8 KB. | None required. | `tests/api/test_api_security.py::TestUnknownFieldsForbidden::test_extra_field_rejected`, `tests/api/test_api_security.py::TestBodySizeLimit::test_large_body_returns_413`, `tests/api/test_api_endpoints.py::TestScenarioE8AT22AT25::test_scenario_invalid_surge_pct_returns_422` PASSED (`reports/logs/sr6-evidence.txt`). |
| **INC-04 Safe error messages** | **APPLICABLE**. Error responses must never leak stack traces, file paths, or DB internals. | **PASS** | Global exception handlers trap `HTTPException`, `RequestValidationError`, and generic `Exception`, returning uniform error envelopes. | None required. | `tests/api/test_api_security.py::TestForcedServerErrorAT34::test_forced_error_envelope` PASSED (`reports/logs/sr6-evidence.txt`). |
| **INC-05 UGC sanitisation & DOM sinks** | **APPLICABLE**. Zero user-generated content stored; client must strictly avoid dangerous DOM sinks. | **PASS** | Zero instances of `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `eval`, or `document.write`. 100% `textContent` / `createElement`. | None required. | `tests/e2e/test_ui_flows.py::TestSecurityAndDOMInertness::test_at_38_static_grep_for_forbidden_dom_sinks` and `test_at_38_xss_payload_in_api_is_inert` PASSED (AT-38). |
| **INC-06 Parameterised database queries** | **APPLICABLE**. All SQL executions must use parameter substitution. | **PASS** | All dynamic values bound via `?` placeholders. DB connected in read-only mode (`?mode=ro`, `PRAGMA query_only = ON`). | None required. | `tests/unit/test_sql_guard.py::test_at_05_sql_guard_no_dynamic_queries` and `tests/api/test_api_security.py::TestReadOnlyDBConnectionFailsWrites::test_write_attempt_raises_error` PASSED (`reports/logs/sr6-evidence.txt`). |
| **INC-07 File upload security** | **NOT APPLICABLE**. No upload endpoints exist. | **N/A** | Zero upload routes. Concrete check `grep -in "multipart" requirements.txt requirements-dev.txt carecast/api/*.py` returned **0 matches** (no multipart dependency or route). | None required. | `grep -in "multipart"` returned 0 matches across `requirements*.txt` and `carecast/api/*.py`. |
| **INC-08 Rate limiting** | **APPLICABLE**. Abuse prevention on public API endpoints. | **PASS** | In-memory sliding-window limiter (`carecast/api/ratelimit.py:20`, `window_seconds=60.0`). Code defaults: `rate_get_per_min = 60`, `rate_post_per_min = 20` (`carecast/settings.py:113-114`, `carecast/api/main.py:93-95`), matching TRD §8 & ASSUMPTION A-10. Both GET limit and POST limit verified via automated tests (HTTP 429 + `Retry-After: 60`). | None required. | `tests/api/test_api_security.py::TestRateLimiterAT35::test_rate_limit_exceeded` (GET) and `test_at_35_post_scenario_rate_limit` (POST) PASSED (`reports/logs/sr6-post-rate-limit.txt`). |
| **INC-09 CSRF protection** | **NOT APPLICABLE**. No cookie-based sessions or authenticated state changes. | **N/A** | No cookies set (`Set-Cookie` absent). E8 is a stateless POST computation. | None required. | `tests/api/test_api_security.py::TestNoCorsAndNoCookiesAT37::test_no_cors_and_no_cookies` PASSED (AT-37). |
| **INC-10 Sensitive data encryption** | **APPLICABLE**. Responses must omit internal paths/IDs; aggregate data only. | **PASS** | No PII or PHI. Schema tests verify only aggregate surveillance counts and rates exist in database. | None required. | `tests/unit/test_schema_constraints.py` PASSED (AT-45). |

---

## 2. Verified UI Evidence & Artifacts

The user interface was reviewed across all responsive viewports with zero security sinks and strict CSP compliance:

- **S1 Cockpit Overview:** `reports/screenshots/p6-s1-overview-1280.png`
- **S2 Forecast Trajectory:** `reports/screenshots/p6-s2-forecast-1280.png`
- **S3 Model Performance:** `reports/screenshots/p6-s3-performance-1280.png`
- **S4 Feature Importance:** `reports/screenshots/p6-s4-explain-1280.png`
- **S5 Capacity Scenario:** `reports/screenshots/p6-s5-scenario-1280.png`
- **S6 Data & Limitations:** `reports/screenshots/p6-s6-data-1280.png`

---

## 3. What I Changed and Why

1. **Production SQLite Multi-Threading Isolation (`carecast/db.py:43`):**
   - *Change:* Added `check_same_thread=False` to SQLite URI connection wrapper (`connect_ro()`).
   - *Reason:* Resolved `sqlite3.ProgrammingError` under concurrent multi-threaded requests dispatched by Uvicorn. Verified by reproduction test `tests/unit/test_concurrency_reproduction.py` and unwrapped E2E test suite (58/58 passed).
2. **Metadata Payload Completeness (`carecast/api/routes.py:356`):**
   - *Change:* Increased quality issue query limit from `LIMIT 50` to `LIMIT 500`.
   - *Reason:* Prevented truncation of documented data anomalies (165 total rows in `data_quality_issues`). Verified by `tests/test_t4_quality_count.py`.
3. **Focus-Ring High-Contrast Styling (`web/assets/css/base.css`, `tokens.css`):**
   - *Change:* Unified all interactive focus rules to `var(--focus-ring)` (`#0B5FFF`, contrast 5.13:1 on white).
   - *Reason:* Standardized WCAG AA compliance across desktop and mobile components.

---

## 4. Residual Risks

1. **In-Memory Rate Limiter State:**
   - In-memory rate limiting state resets when the application process restarts. Acceptable for MVP local/single-process deployment; production multi-instance clusters would require Redis or an upstream reverse proxy rate limiter.
2. **Empirical Prediction Interval Miscalibration (Issue 1):**
   - Disclosed in `reports/known-issues.md`. Statistical limitation of static empirical residual pools during seasonal regime changes. Decision-support guidance only; does not impact runtime application security.


