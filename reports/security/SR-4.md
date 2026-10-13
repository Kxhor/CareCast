# Incremental Security Review 4 (SR-4) — Phase 5

**Date / Time:** 14 Oct 2026  
**Scope:** Phase 5 Frontend Core Build (`web/index.html`, `web/assets/css/*`, `web/assets/js/*`, `web/vendor/*`, `web/assets/icons.svg`, `tests/e2e/test_ui_flows.py`, `scripts/capture_screenshots.py`)  
**Target:** Client-Side Architecture, DOM Security, Content Security Policy (CSP) Compliance, Third-Party Dependency Security, and State Storage Isolation  
**Review Type:** Incremental Review (Master Prompt #1 / TRD §9.3 INC-01...INC-10)

---

## 1. Security Checklist (INC-01 – INC-10)

| Control | Applicability & Rationale | Status | Findings | Fix / Mitigation | Evidence |
|---|---|---|---|---|---|
| **INC-01 Permission checks** | **NOT APPLICABLE** (D-04). Public aggregated respiratory surveillance dashboard. No authentication, authorization, or user accounts. | **N/A** | All endpoints consumed via GET/POST are public aggregate views. No sensitive role-based access exists on the client. | N/A | Zero authorization headers or tokens generated or expected. |
| **INC-02 Secrets, API keys, tokens** | **APPLICABLE**. Client-side bundle, HTML, CSS, and JS must contain zero hardcoded secrets, private keys, or API credentials. | **PASS** | Automated scan of all files under `web/` returned clean. | None required. | `git grep -nEi "(api[_-]?key\|secret\|token\|passwd)" -- web/` clean (0 matches). |
| **INC-03 User input validation** | **APPLICABLE**. Hash routes and user-entered capacity planning inputs (surge percentage, staffed beds, turnover days) must be strictly validated before processing. | **PASS** | Hash routes validated against canonical allowlist (`#/overview`, `#/forecast`, `#/performance`, `#/explain`, `#/scenario`, `#/data`). Surge slider strictly constrained to $[-50, 100]$. Capacity inputs clamped to physical lower bounds ($\ge 0$). Invalid inputs fail gracefully without corrupting state. | Input clamping and type coercion in `store.js`. | `test_ui_flows.py::TestScenarioS5::test_at_23_scenario_badge_and_slider_update` PASSED. |
| **INC-04 Safe error messages** | **APPLICABLE**. UI error states must present human-friendly fallback notices without disclosing system internals, stack traces, or server topologies. | **PASS** | When API requests fail or time out, `components.renderAlert()` renders a standard non-technical warning card (`"Unable to load data. Please retry."`). No raw JSON errors, tracebacks, or server paths injected into the DOM. Independent widget error isolation prevents whole-screen crashes. | Structured error handling in `api.js` and individual view renderers. | Verified in `test_disease_switching` and widget test suites. |
| **INC-05 UGC sanitisation & DOM XSS** | **CRITICAL / APPLICABLE**. All dynamic data from API responses must be rendered safely without introducing Cross-Site Scripting (XSS) injection vectors. | **PASS** | **ZERO dynamic HTML sinks**: static scan found 0 occurrences of `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `eval()`, `new Function()`, or `document.write()`. All elements constructed using `document.createElement`, `document.createTextNode`, and `.textContent`. Automated AT-38 test injected `<img src=x onerror=alert(1)>` into API payloads; verified payload rendered purely as inert text with 0 DOM script execution. | Strict DOM building primitives in `components.js` and view modules. | `test_ui_flows.py::test_at_38_xss_payload_in_api_is_inert` and `test_at_38_static_grep_for_forbidden_dom_sinks` PASSED. |
| **INC-06 Parameterised SQL** | **NOT APPLICABLE (Client)**. Frontend has no direct database connectivity. Queries are dispatched to parameterized backend endpoints (E1–E8). | **N/A** | All queries routed through API client (`api.js`) to backend endpoints. | Backend SQL guard verified in SR-3. | Backend AST test `test_sql_guard.py` PASSED. |
| **INC-07 File uploads** | **NOT APPLICABLE**. Application contains zero file upload controls, multipart forms, or drag-and-drop file ingestion handlers. | **N/A** | No file input elements (`<input type="file">`) exist in `web/index.html` or DOM components. | N/A | Static grep confirms 0 file inputs. |
| **INC-08 Rate limiting & client throttling** | **APPLICABLE**. Interactive controls (slider in Scenario Planner S5) must not flood the backend API with unthrottled burst requests. | **PASS** | Surge slider input events are debounced with a 300ms window (`debounce(..., 300)`). Instant calculations update local UI estimates; backend queries are rate-managed. | Debounce utility active on S5 input events. | S5 interactive testing shows single dispatched request per slider resting position. |
| **INC-09 CSRF & Session Security** | **NOT APPLICABLE**. Application issues zero cookies (`Set-Cookie` absent), maintains no sessions, and uses no credentials. | **N/A** | Security middleware actively strips cookie and CORS headers. `localStorage` is used solely for non-sensitive local capacity planning overrides (`carecast.capacity.v1`). | All `localStorage` access wrapped in defensive `try/catch` with fallback in-memory defaults. | `test_api_security.py::TestNoCorsAndNoCookiesAT37` PASSED. |
| **INC-10 Sensitive data exposure & CSP** | **CRITICAL / APPLICABLE**. Frontend must strictly adhere to Content Security Policy (TRD §9.2), avoid inline styles/scripts, and eliminate third-party CDN leaks. | **PASS** | 1. **CSP Strictness**: Zero inline `<style>` tags or `style="..."` attributes across all HTML and SVG assets. Zero inline `<script>` tags or `on*` event attributes.<br>2. **Zero CDNs**: All assets (CSS, JS, fonts, icons, Chart.js) served from same-origin (`/assets/`, `/vendor/`).<br>3. **Vendored Chart.js**: v4.4.7 UMD extracted from official npm package; verified clean of known CVEs; SHA-256 and MIT license logged.<br>4. **Browser Console**: Verified 0 CSP violations and 0 console errors across all routes in live headless browser. | Full adherence to CSP `style-src 'self'`, `script-src 'self'`, `img-src 'self' data:`. Favicon 404 silenced via clean data URI. | `verify_console_routes.py` PASSED with 0 console errors and 0 page errors. |

---

## 2. Automated Security & Static Analysis Scans

### A. Static DOM Sink Grep Audit (AT-38)
- **Command:** `Get-ChildItem -Path web/assets/js -Recurse -Filter *.js | Select-String -Pattern 'innerHTML|outerHTML|insertAdjacentHTML|eval\(|new Function|document\.write' -AllMatches`
- **Output:** Clean — 0 matches.
- **Assessment:** Absolute compliance with strict DOM building requirements.

### B. Inline Style & Script Audit (CSP Compliance)
- **Command:** `Get-ChildItem -Path web -Recurse -Include *.html,*.svg | Select-String -Pattern 'style=' -AllMatches`
- **Output:** Clean — 0 matches.
- **Assessment:** Zero inline styles exist in client markup or SVG sprites. All layout and presentation governed by `tokens.css`, `base.css`, `layout.css`, and `components.css`.

### C. Secret & Credential Scan
- **Command:** `git grep -nEi "(api[_-]?key|secret|token|passwd|password|bearer|private[_-]?key)" -- web/`
- **Output:** Clean — 0 secrets found.

### D. Third-Party Dependency Security (Chart.js)
- **File:** `web/vendor/chart.umd.js`
- **Version:** Chart.js 4.4.7 UMD
- **SHA-256 Checksum:** `2812cb8825fdc57469eb2f7bb055e9429244e599920511ee477e828499b632cb`
- **Source:** Official npm package tarball `https://registry.npmjs.org/chart.js/-/chart.js-4.4.7.tgz`
- **Advisory Review:** Public GitHub Security Advisories and npm audit checked. Zero known high or critical CVE vulnerabilities affect Chart.js v4.4.7.
- **Documentation:** Recorded in `web/vendor/VERSIONS.md` and `web/vendor/LICENSES.md`.

---

## 3. What Was Added and Why

1. **Pure Element DOM Construction (`web/assets/js/components.js`, `views/*.js`)**:
   - Every UI element, card, table, badge, and status pill is generated via `document.createElement`, `.classList.add()`, and `document.createTextNode` or `.textContent`. This structurally eliminates DOM-based XSS, even if an upstream API field were compromised with arbitrary HTML payloads.
2. **Defensive `localStorage` Wrapper (`web/assets/js/store.js`)**:
   - Browser environments with strict privacy settings, storage quotas, or disabled storage (e.g., incognito mode or iframe restrictions) throw exceptions on `localStorage` access. All reads and writes to `carecast.capacity.v1` are guarded in `try / catch` blocks with transparent in-memory fallback.
3. **Strict Route Parameter Sanitization (`web/assets/js/router.js`, `store.js`)**:
   - URL hash routing parses route segments and query parameters (`?disease=...`, `?jurisdiction=...`). Unrecognized routes default cleanly to `#/overview`; unrecognized disease codes default to `influenza`.
4. **Honesty & Operational Badging**:
   - Tier indicators display both text and icon; simulated scenarios are prominently badged (`SCENARIO — not a prediction`, `SIMULATED — assumption-based`); all screens feature a persistent footer disclaimer to prevent user confusion with direct clinical forecasts.

---

## 4. Residual Risks

1. **Third-Party Script Execution Risk**:
   - While Chart.js v4.4.7 is vendored, pinned, and hash-verified, client-side graphing libraries inherently execute complex canvas drawing algorithms. Mitigation: Script is pinned to a static file on disk; CSP blocks external script loading; integrity hash verified.
2. **Browser Storage Cleared**:
   - Capacity assumptions entered by the user in S5 are stored only in client `localStorage`. If the user clears browser data or changes browsers, customized assumptions reset to default demo placeholders (`config/planning.toml`). This is intentional by design to maintain a stateless backend.
