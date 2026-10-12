# ANTIGRAVITY_PROMPTS — Copy-Ready Prompts

| Field | Value |
|---|---|
| Document | `docs/ANTIGRAVITY_PROMPTS.md` (7 of 8) |
| Version / status | 1.0 — **DRAFT FOR USER APPROVAL** |
| Date | 10 Oct 2026 |
| Depends on | All other docs · `GLOBAL_SKILLS_REPORT.md` · `Master_security_prompts.txt` |

## 0. How to use

1. Put the eight docs in the repo's `docs/` folder and commit them.
2. Start a **new Antigravity session** for each phase. Paste **G-0 (Global rules)** first, then the phase prompt.
3. The agent must stop at the end of the phase. You reply with the approval message from §8. The agent then tags `phase-N-approved`.
4. If something fails, paste the matching **RV-n** prompt (§5).
5. Security reviews (§6) are *part of* phases P2–P7 — they are already referenced in the phase prompts.
6. Fenced prompt blocks use four backticks so they can contain code.

**Skill note.** `GLOBAL_SKILLS_REPORT.md` says the skills trigger automatically. The prompts still *name* them so their use is deliberate and reportable. Skill behaviour is as described in that report; I have not tested it.

**Placeholders:** `<N>` = phase number; `<last>` = the last approved git tag.

---

## 1. G-0 — Global rules (paste at the start of every session)

````text
PROJECT: CareCast — explainable respiratory-admission forecasting and capacity early-warning (college project; decision support only; NOT clinically validated).

SOURCE OF TRUTH: the eight documents in docs/: PRD.md, TRD.md, APP_FLOW.md, UI_UX_DESIGN.md, BACKEND_SCHEMA.md, IMPLEMENTATION_PLAN.md, ANTIGRAVITY_PROMPTS.md, FINAL_PROJECT_AUDIT.md. Do not contradict them. If you believe one is wrong, STOP and ask me.

OPERATING RULES
1. INSPECT FIRST. Before changing anything: run `git status`, list the repository tree, read the docs required by this phase, and report what already exists.
2. ONE PHASE AT A TIME. Complete and validate only the current phase. Never start the next phase. After your phase report, STOP and wait for my exact reply "APPROVED: PHASE <N>".
3. EVIDENCE, NOT CLAIMS. Every validation must be a real command you ran. Save raw output to reports/logs/<phase>-<name>.txt and quote the real result. Never fabricate, estimate, or "expect" results. If you cannot run something, say "NOT RUN" and why.
4. FAILURES. If validation fails: use systematic-debugging, fix within the current phase, re-run the relevant checks, and document the failure, root cause and fix in the phase report. Do not mark the phase complete while required checks fail.
5. NO SILENT CHANGES. Do not change approved architecture, scope, schema, API contract or dependencies without asking me first. Ask with: what, why, alternatives, impact.
6. NO MOCKS FOR REQUIRED FEATURES. Do not hard-code demo numbers in place of data from the database/API. Do not claim an unfinished feature is complete.
7. ML HONESTY. Use chronological splits only; no random shuffling; no fitting or selecting on the test block; always compare with the persistence baseline; never invent performance thresholds; never imply clinical validity. If the model does not beat the baseline, report that plainly.
8. SIMULATED CONTENT must be labelled (SIMULATED / SCENARIO). Test fixtures are TEST-ONLY and never shown in the UI or shipped.
9. MINIMALISM (Ponytail). Before adding code: is it needed? does it exist? stdlib? platform? installed package? one line? Then minimum code. No new dependency without approval.
10. SECURITY. Fix confirmed security vulnerabilities and re-validate. For functional (non-security) defects OUTSIDE the current phase scope: do NOT fix; log them in reports/known-issues.md with evidence and a suggested fix.
11. SKILLS TO APPLY: Superpowers (brainstorming, test-driven-development, systematic-debugging, verification-before-completion); Ponytail; Matt Pocock (domain-modeling, codebase-design, diagnosing-bugs) for backend/data; Taste Skill + Impeccable for UI; Security Review (incremental / prelaunch / audit-log).
12. REPORTING. End with reports/phase-<N>.md using the template in IMPLEMENTATION_PLAN.md §3 and paste the filled gate checklist from §6 of that document.
13. When I reply "APPROVED: PHASE <N>", create git tag phase-<N>-approved before doing anything else.
````

---

## 2. P-00 — Repository inspection & readiness (optional first run)

````text
Apply G-0. Do NOT modify any file in this task.
1. Run: git status; git log --oneline -n 20; list the repo tree to depth 3.
2. Confirm docs/ contains the eight files. List missing ones.
3. Report tool availability by running: python --version; pip --version; git --version; node --version (informational only); and whether you have network access (try `pip download --no-deps pip -d /tmp/x`, report the real result).
4. Report whether a browser is available for Playwright, and whether you can reach https://data.cdc.gov (real result only).
5. Summarise (max 15 lines): what exists, what is missing, risks for Phase 1.
STOP. Do not start Phase 1.
````

---

## 3. Phase prompts

### P-1 — Setup & repository audit

````text
Apply G-0. PHASE 1 — Project setup & repository audit.
READ FIRST: all eight docs; GLOBAL_SKILLS_REPORT.md; Master_security_prompts.txt.
SKILLS: brainstorming (briefly, to confirm the plan), Ponytail, verification-before-completion.

TASKS
1. Repo audit: report existing files/branches/commits and anything that conflicts with TRD §13. Do not delete user files; ask first.
2. Create the folder layout in TRD §13 (modules may contain only a module docstring).
3. Create a virtual environment, install ONLY the dependencies in TRD §3.2, then write exact pinned versions (from `pip freeze` of what you really installed) to requirements.txt and requirements-dev.txt.
4. Create .gitignore (venv, .env, data/raw/, data/*.db, caches, reports/screenshots optional), .dockerignore, .env.example (variables in TRD §8, no secrets).
5. Implement carecast/settings.py (env + TOML loading with validation, fail-fast with clear errors) and carecast/db.py (connect_rw, connect_ro with mode=ro + PRAGMA query_only=ON + foreign_keys=ON, migration runner skeleton).
6. Add pytest config, ONE smoke test, and a unit test that settings reject an invalid value.
7. Create scripts/verify.py skeleton (runs pytest, pip-audit, exits non-zero on failure).
8. README.md: setup and commands from TRD §12.

VALIDATION (run and save outputs): clean-venv install; python -m pytest -q; python -c "import carecast"; pip-audit (save output; record findings, do not hide); git grep for secrets.
ACCEPTANCE: see IMPLEMENTATION_PLAN P1. No dependency outside TRD §3.2.
Write reports/phase-1.md. STOP and wait for "APPROVED: PHASE 1".
````

### P-2 — Data acquisition, validation & database

````text
Apply G-0. PHASE 2 — Data acquisition, validation & database. (Feature F1)
READ FIRST: PRD §2.4–2.5 and F1; BACKEND_SCHEMA (all); TRD §5.1, §9.3.
SKILLS: domain-modeling, codebase-design, test-driven-development, systematic-debugging, Ponytail, Security Review (incremental), verification-before-completion.

TASKS
1. Write migrations/0001_core_data.sql and 0002_forecasting.sql EXACTLY as in BACKEND_SCHEMA §3. Implement the migration runner (one transaction per file, records version, skips applied). Write tests that apply them to a fresh DB.
2. DATA: obtain the CDC CSVs (dataset ids in PRD §2.5: ua7e-t2fy primary candidate, vdzy-6i9v secondary). If you have no network/browser access, STOP and ask me to place the CSV files in data/raw/. Never invent data or column names.
3. Inspect the REAL headers. Fill config/dataset_mapping.toml. Produce the DATA DECISION RECORD in reports/phase-2.md: headers found; whether a weekly new-admission COUNT exists per disease (else RATE); national jurisdiction value; reporting-coverage column; licence/terms text you found; the date range; the number of weeks per disease.
4. Implement ingest.py (F1.1–F1.6) and quality.py. Raw files are read-only; record SHA-256 and row count in dataset_sources. Parameterised SQL ONLY (no string-built SQL).
5. EDA per disease (tables/plots saved in reports/): seasonality, zeros, missing weeks, coverage changes, and any regime breaks (reporting rules changed over time: mandatory → voluntary → CMS-required; RSV voluntary until 1 Nov 2024). Propose a training_start and which diseases qualify. Do not decide for me.
6. Write tests (tests/unit/): AT-01, AT-02, AT-03, AT-04, AT-05, AT-45, plus negative DB-constraint tests (non-Saturday date; train/valid/test overlap).
7. Tiny TEST-ONLY fixtures in tests/fixtures/ (deterministic synthetic, labelled).

VALIDATION: run the tests; `python -m carecast.pipeline migrate && ingest && check`; run ingest a second time (must add 0 rows); compare DB counts with the filtered CSV counts and show both numbers.
SECURITY: run the INCREMENTAL security review (prompt SR in ANTIGRAVITY_PROMPTS §6.2) on the new code → reports/security/SR-1.md.
Write reports/phase-2.md. STOP and wait. My approval message will include decisions OD-03 (target) and OD-06 (training start).
````

### P-3 — Forecast engine & evaluation

````text
Apply G-0. PHASE 3 — Forecast engine & evaluation. (Features F3, F4, F6, F12)
READ FIRST: TRD §5 (all); PRD F3–F6, A-04…A-07; BACKEND_SCHEMA T7–T11; the approved Data Decision Record.
SKILLS: domain-modeling, test-driven-development, systematic-debugging, Ponytail, Security Review (incremental), verification-before-completion.

TASKS
1. config/pipeline.toml (split 0.6/0.2/0.2, horizons 1–4, features, candidates, interval level 0.8, threshold percentile 75, refit stride, permutation repeats, random_seed, training_start from my approval).
2. features.py: lag0–lag3, roll_mean_4, seasonal_lag52 (only if history allows), woy_sin/cos of the TARGET week, pct_reporting if mapped. Leak-free by construction.
3. models.py: baseline_persistence, baseline_seasonal_naive (if available), linear_lag (LinearRegression), hgb_lag (HistGradientBoostingRegressor, fixed random_state). Clip negative predictions to 0 and record it.
4. evaluate.py: chronological split on target weeks; walk-forward (training rows for a refit at origin t are those with s+h<=t); metrics MAE, RMSE; validation-only model selection per horizon; empirical residual quantiles (q10/q90 of validation residuals) for intervals; interval coverage on TEST; beats_persistence on TEST (strictly lower MAE).
5. explain.py: linear contributions (coef x (x - train mean)) with __base__ so that base + sum = prediction; permutation importance on the validation block; templated plain-language text using "associated with" language only.
6. pipeline.py train: one transaction per series; set previous run is_current=0; persist T7–T11; store library versions, config hash, raw SHA-256, code_version (git commit) in config_json.
7. Tests: AT-08 (leakage perturbation), AT-11, AT-12, AT-13, AT-14 (logic, both branches), AT-18, AT-43, AT-10 (storage).
8. Do NOT: shuffle, tune on test, pickle/joblib models, add XGBoost/SARIMA/SHAP, apply any pass/fail threshold to metrics.

VALIDATION: run tests; run `python -m carecast.pipeline train` TWICE and diff the stored metrics (must be identical, show the diff command and output).
REPORT: for each available disease give split dates/sizes and a table of MAE/RMSE per model x horizon x split, selected model per horizon, beats_persistence, test interval coverage, top contributions. Raw numbers only. State plainly where the models do not beat persistence.
SECURITY: incremental review → reports/security/SR-2.md (expect many N/A with reasons).
STOP and wait for "APPROVED: PHASE 3".
````

### P-4 — Backend API & planning logic

````text
Apply G-0. PHASE 4 — Backend API & planning logic. (F2–F11 API side)
READ FIRST: BACKEND_SCHEMA §7–§10; TRD §4, §6, §9; PRD F5, F7–F10.
SKILLS: domain-modeling, codebase-design, test-driven-development, systematic-debugging, Ponytail, Security Review (incremental), verification-before-completion.

TASKS
1. planning.py as PURE functions: tier(point, lower, upper, threshold) per PRD F5.2; scenario(surge_pct); capacity_illustration(...) per PRD F8.2 (handle reference_level = 0); action checklists by tier.
2. config/planning.toml: capacity placeholders (choose neutral demo values and LABEL them "DEMO PLACEHOLDER — not data"), bounds, actions, limitations L-01…L-12 verbatim from PRD §9, disclaimer.
3. API (carecast/api/): endpoints E1–E8 exactly as BACKEND_SCHEMA §8; Pydantic models with extra="forbid"; enums validated against the DB; read-only DB connection; parameterised SQL; target column chosen from a hard-coded allow-list.
4. HTTP hardening: security headers (TRD §9.2), body-size cap 8 KB, in-memory rate limiter (GET and POST limits from env), request-id, generic error envelope (BACKEND_SCHEMA §7.1), /docs /redoc /openapi.json disabled unless CARECAST_ENV=dev and CARECAST_ENABLE_DOCS=1, NO CORS middleware, NO cookies, static mount for web/ (placeholder index.html).
5. Generate tests/contract/openapi.snapshot.json from app.openapi().
6. Tests: AT-06, AT-09, AT-10 (API), AT-15 (boundary table), AT-16, AT-19, AT-21, AT-22, AT-24, AT-25 (API), AT-26, AT-28, AT-30, AT-33, AT-34 (force an exception), AT-35, AT-37, plus a test that writes through the API connection FAIL.
7. Manually call every endpoint with curl against the REAL database; save outputs.

SECURITY: full INCREMENTAL review (all 10 items) of the new code → reports/security/SR-3.md. Fix confirmed vulnerabilities and re-validate.
STOP and wait for "APPROVED: PHASE 4".
````

### P-5 — Frontend core build

````text
Apply G-0. PHASE 5 — Frontend core build. (UI for F2–F12)
READ FIRST: UI_UX_DESIGN (all), APP_FLOW (all), TRD §7, §9.2; look at Reference_Ui.jpg.
SKILLS: Taste Skill (write the one-line Design Read; use VARIANCE low, MOTION minimal, DENSITY medium-high on the skill's own scale), Impeccable (Operate mode for S1–S5, Read mode for S6), test-driven-development, systematic-debugging, Ponytail, Security Review (incremental), verification-before-completion.

BEFORE CODING: run the backend suite and save the result + the sha256 of tests/contract/openapi.snapshot.json (baseline for regression R1).

TASKS
1. web/: tokens.css (verbatim from UI_UX_DESIGN §3), base/layout/components CSS; ES modules (app, router, store, api, charts, format, components, views); icons sprite (own simple SVGs); NO inline style attributes; NO CDN.
2. Vendor Chart.js: exact pinned version in web/vendor/, SHA-256 + version + licence in VERSIONS.md/LICENSES.md; check public advisories for that version and record the result. Ask me before choosing a version if unsure.
3. Implement S1–S6 exactly per APP_FLOW §4 with ALL states in §5 and the adaptation map in UI_UX_DESIGN §2 (own brand "CareCast"; NO Apollo name/logo/avatars/illustrations).
4. Render ALL API data with textContent / createElement only. NEVER use innerHTML, outerHTML, insertAdjacentHTML, eval, new Function with dynamic data.
5. Honesty markers: tier text+icon, SIMULATED and SCENARIO badges, footer disclaimer on every screen, verdict text exactly per UI_UX_DESIGN §7.
6. localStorage only inside try/catch for capacity assumptions; validate URL hash params.
7. Playwright E2E tests: AT-07, AT-14 (E2E, both branches via fixture DB), AT-17, AT-20, AT-23, AT-25 (E2E), AT-27, AT-29, AT-31 (change fixture DB values → UI changes), AT-32, AT-38 (inject <img onerror> via a mocked API field → inert).
8. Do NOT modify backend code. If you believe the backend must change, STOP and ask me.

VALIDATION: backend suite again (must equal baseline); contract snapshot sha256 unchanged (AT-47/R1); E2E; check the browser console for errors and CSP violations on every route; grep for forbidden DOM sinks. Capture screenshots of each screen from the REAL running app (verify files exist) and list them in the report.
SECURITY: INCREMENTAL review of the new frontend code → reports/security/SR-4.md.
STOP and wait for "APPROVED: PHASE 5".
````

### P-6 — UI polish, accessibility & responsive fidelity

````text
Apply G-0. PHASE 6 — UI polish, accessibility and responsive fidelity.
READ FIRST: UI_UX_DESIGN §1–§3, §6, §9, §10; Reference_Ui.jpg; reports/phase-5.md.
SKILLS: Impeccable (polish, a11y, contrast), Taste Skill (anti-slop), systematic-debugging, Ponytail, Security Review (incremental), verification-before-completion.

BEFORE CODING: backend suite + openapi snapshot hash baseline (regression R2).

TASKS
1. Compare S1 at 1280 px with Reference_Ui.jpg side by side. Close gaps ONLY where UI_UX_DESIGN §2 does not list an adaptation.
2. Work through the A11Y-01…A11Y-14 checklist; record evidence for each (computed contrast table, keyboard run notes, DOM checks, Lighthouse findings with version — do not claim a pass without evidence).
3. Responsive behaviour per UI_UX_DESIGN §6; no horizontal body scroll at 320, 375, 768, 1280 px.
4. Write scripts/capture_screenshots.py (Playwright; real app in prod mode; real DB). Capture every screen at 320/375/768/1280/1440 into reports/screenshots/<phase>-<screen>-<width>.png. Verify each file (ls -l, sha256sum, image dimensions) and list them.
5. VC-01…VC-16: pass/fail + screenshot for each. List deviations with reasons.
6. CSS/JS/HTML changes ONLY. NO backend changes.

VALIDATION: E2E at breakpoints (AT-41); a11y checklist (AT-40); VC review (AT-42); backend suite + contract hash identical (AT-47/R2).
SECURITY: INCREMENTAL review of the polish diff only → reports/security/SR-5.md.
STOP and wait for "APPROVED: PHASE 6". In your report, ask me for decisions OD-05 (attempt F13?) and OD-04 (deployment target).
````

### P-7 — Testing hardening, pre-launch review, deployment & final audit

````text
Apply G-0. PHASE 7 — Testing hardening, pre-launch security review, deployment and final audit.
READ FIRST: TRD §9.3, §10, §12; IMPLEMENTATION_PLAN P7; FINAL_PROJECT_AUDIT.md; Master_security_prompts.txt; all reports/.
SKILLS: Security Review (prelaunch + audit-log), verification-before-completion, systematic-debugging, Ponytail.

TASKS
1. Fresh clone into a new folder. Install. `python -m carecast.pipeline rebuild`. `python scripts/verify.py`. Save raw outputs.
2. Run EVERY acceptance test AT-01…AT-47 (AT-46 deferred) and record result + evidence.
3. PRE-LAUNCH security review: use prompt PL in ANTIGRAVITY_PROMPTS §6.3 → reports/security/PL.md. Fix confirmed vulnerabilities, re-validate, record.
4. Prod-mode checks: CARECAST_ENV=prod → /docs, /redoc, /openapi.json return 404; no Access-Control-* and no Set-Cookie; headers present.
5. Deployment per my decision OD-04 given in my Phase 6 approval (local / Docker non-root with HEALTHCHECK / free-tier PaaS). If it is missing, ASK before deploying. Verify the container or deployment really runs; save outputs. HTTPS controls are N/A for local HTTP — say so.
6. Populate docs/FINAL_PROJECT_AUDIT.md using prompts FA-1, FA-2, FA-3 (§7). Use ONLY recorded evidence. Do not add anything new.
7. For UNRELATED functional errors found during the audit: DO NOT FIX. Record symptom, evidence, severity, suggested fix.
STOP and wait for "APPROVED: PHASE 7".
````

---

## 4. Feature implementation prompts

### 4.1 Template (use when a single feature needs rework or when implementing outside a phase prompt)

````text
Apply G-0. Implement/repair FEATURE <Fx — name> only.
READ: PRD feature section and its acceptance tests; the rows for <Fx> in PRD §12; APP_FLOW widgets; BACKEND_SCHEMA endpoints; UI components.
PLAN FIRST (brainstorming): list files to touch, tests to write first (AT-…), and what you will NOT touch.
DO: write failing tests → minimum code to pass → run the whole suite → report real output.
DON'T: change other features, schema, contract or dependencies; add mock data.
Report: files changed, tests added, raw results, deviations. STOP.
````

### 4.2 Feature-specific prompts (paste after G-0)

| Feature | Prompt body |
|---|---|
| **F1** | `Implement F1 per PRD F1.1–F1.6 and BACKEND_SCHEMA §1/§3. Tests AT-01…AT-05, AT-45 first. Raw CSV is read-only; aborts on missing mapped columns; never drop rows silently.` |
| **F2** | `Implement F2: E4 (BACKEND_SCHEMA §8) with from/to validation, then S1 w-trend and S2 w-forecast-chart. Imputed weeks must be visually distinct. Tests AT-06, AT-07.` |
| **F3** | `Implement F3 per TRD §5.1–5.3. First write the leakage test AT-08 (perturb values after origin t; forecast at t unchanged). Direct strategy, horizons 1–4, intervals from validation residuals. Tests AT-08, AT-09, AT-10.` |
| **F4** | `Implement F4: chronological 60/20/20 walk-forward, MAE/RMSE, coverage, beats_persistence. No thresholds. UI verdict text must come from stored comparison (both branches). Tests AT-11…AT-14.` |
| **F5** | `Implement F5: planning.tier() pure function; boundary table tests first (AT-15); threshold validation (AT-16); UI shows tier text+icon+threshold+disclaimer (AT-17).` |
| **F6** | `Implement F6: linear contributions with __base__ (additive identity test AT-18), permutation importance on validation block, templated text with no causal wording (AT-19), UI bars sorted by |value| (AT-20); handle hgb_lag by showing importance only.` |
| **F7** | `Implement F7: scenario math adjusted = base*(1+pct/100) for point/lower/upper; bounds -50..100; badge "SCENARIO — not a prediction". Tests AT-21…AT-23.` |
| **F8** | `Implement F8 per PRD F8.2 with the worked-example test AT-24; reference_level = 0 edge case; is_simulated=true; badge "SIMULATED — assumption-based". Placeholders labelled as not data. Tests AT-24, AT-25.` |
| **F9** | `Implement F9: static tier→checklist from config/planning.toml; footer "Final decisions rest with authorised staff." Tests AT-26, AT-27.` |
| **F10** | `Implement F10: E2 provenance (source, dataset id, retrieved_at, sha256, data_as_of), footer on all screens, S6 lists L-01…L-12 and all quality findings. Tests AT-27…AT-29.` |
| **F11** | `Implement F11: E3 aggregation and S1 widgets per APP_FLOW §4; each widget fails independently; no hard-coded numbers (AT-31). Tests AT-30, AT-31.` |
| **F12** | `Implement F12: available flag per disease from validation results; top-bar select + watchlist switch all widgets; unavailable shows reason. Test AT-32.` |
| **F13** | `DO NOT IMPLEMENT unless I have explicitly approved OD-05. If approved: reuse the same pipeline per state; ask before any schema change.` |

---

## 5. Failed-validation recovery prompts

### RV-1 — General failure

````text
Apply G-0. A validation in the current phase FAILED. Do not start new work.
1. Paste the exact failing command and the full raw output.
2. Use systematic-debugging: state a hypothesis, the evidence for it, and a test that reproduces the failure BEFORE changing code.
3. Identify the ROOT CAUSE (not a symptom). If the cause is outside the current phase, stop and tell me.
4. Fix with the minimum change (Ponytail). Add or adjust a regression test.
5. Re-run the failed check AND the whole phase suite; paste raw output.
6. Add a row to the debugging history in reports/phase-<N>.md: symptom, root cause, fix, verification, evidence path.
7. If the fix needs an architecture, schema, contract or dependency change: STOP and ask me.
STOP and wait.
````

### RV-2 — Model does not beat the baseline (or results look implausible)

````text
Apply G-0. The selected model does not beat the persistence baseline, or the results look implausible.
1. DO NOT tune on the test block, change the split to improve numbers, add models, or hide the comparison.
2. Check for leakage (re-run AT-08), target/feature alignment (origin vs target week), unit issues (count vs rate), regime-break effects (plot residuals over time), and missing-week handling.
3. Report the evidence for each check (raw numbers/plots).
4. If a legitimate bug is found: fix it, re-run the full pipeline twice, show identical metrics, and report before/after honestly.
5. If NO bug is found: keep the result. The product must say "did not improve on the baseline" (PRD F4.3). Propose options (e.g., different training_start, fewer features) and WAIT for my decision; do not apply them.
STOP and wait.
````

### RV-3 — A security fix fails validation

````text
Apply G-0. A security fix did not pass re-validation.
1. Show the original finding (SR/PL id, item, evidence), the fix you applied, and the failing check output.
2. Do not disable the control to make a test pass. Do not weaken CSP, validation, or read-only access.
3. Find why the fix is ineffective; apply a corrected fix; re-run the specific test plus the full suite.
4. Update reports/security/<id>.md with the final status. If you cannot resolve it, mark BLOCKED with the reason and the risk, and ask me.
STOP and wait.
````

### RV-4 — Frontend change appears to have affected the backend (regression)

````text
Apply G-0. The backend suite or the OpenAPI contract snapshot differs from the baseline after frontend work.
1. Show: baseline results (path), current results, and the diff of tests/contract/openapi.snapshot.json (sha256 before/after).
2. Identify the exact commit/files that changed backend behaviour. Frontend phases must NOT change backend code.
3. Revert the backend-affecting change or, if it was necessary, ask me before keeping it.
4. Re-run the backend suite and the snapshot comparison; paste raw output.
STOP and wait.
````

### RV-5 — Real data does not match the documented assumptions

````text
Apply G-0. The real CSV headers/values do not match the mapping or assumptions (e.g., no count column, different jurisdiction value, gaps, unexpected units).
1. Paste the real headers and a 5-row sample (no invented values).
2. List which assumptions fail (PRD A-03, A-13, BACKEND_SCHEMA §1) and why.
3. Propose up to three options with impacts. Do NOT choose silently and do NOT fabricate or synthesise data.
STOP and wait for my decision (OD-03).
````

---

## 6. Security review prompts

### 6.1 Your two master prompts — VERBATIM (source: `Master_security_prompts.txt`)

> This block is copied unchanged so the final audit can be checked against the original. Do not edit it.

````text
#1 We just finished building (name it, a new feature, ui, any backend changes) now. 
Review only  the new code for security issues. Check each of these specifically:
(1) Are there permission checks on every endpoint — both authentication (is the user  logged in?) and authorization (are they allowed to access this specific 
resource)? 
(2) Are there any hardcoded secrets, API keys, or tokens? 
(3) Is user input validated on the backend, not just the frontend? 
(4) Are error messages safe — no stack traces, file paths, or database details exposed to the user? 
(5) Is all user-generated content sanitized before being stored or displayed? 
(6) Are database queries using parameterized queries, not string concatenation?
(7) If there are file uploads, are they validated and stored securely? 
(8) Is there rate limiting on any endpoint that could be abused? 
(9) Are there any CSRF vulnerabilities in state-changing operations? 
(10) Is sensitive data encrypted and not over-exposed in API responses? 
Flag  everything you find, fix it, and then tell me what you changed and why.


#2 Pre-Launch Review (run this once, right before going live, not now)

Do a comprehensive security review of the entire codebase. 
Check: 
(1) All secrets are in environment variables, not in code. 
(2) All user input is validated on the backend. 
(3) All database queries use parameterized queries. 
(4) All API endpoints have authentication and authorization checks. 
(5) Error messages don't expose internal details. 
(6) CORS is locked to my domain only. 
(7) Debug mode is off. 
(8) All cookies have secure, http Only, and sameSite flags. 
(9) HTTPS is enforced everywhere. 
(10) Rate limiting is in place on login and sensitive endpoints. 
(11) File uploads are validated and stored securely. 
(12) Dependencies have no known critical vulnerabilities. 
(13) No test credentials, dummy data, or development artifacts remain. Give me a pass/fail for each item and fix anything that fails.

After completing these two master security reviews, I want you to create an md file consisting a very detailed context of what the prompts + 2 master security review prompts, the debugging you did have done. I'm gonna verify it against my Ai assistant so don't leave behind anything or don't introduce new things. Make it very detailed and I also want you to take screenshots of the current Ui and status of the complete project and attach it to the md file under the respective prompts...
Check these and include it in the md file too :
1) Has our frontend changes disturbed the backend functionality?
2) Is our project working properly without any errors after our master review, if any what is it and suggest way to fix it. Don't fix them just flag them and put them in the md file
````

### 6.2 SR — Incremental review (adapts Master Prompt #1; run after P2, P3, P4, P5, P6)

````text
Apply G-0. INCREMENTAL SECURITY REVIEW for Phase <N> → output reports/security/SR-<k>.md (k = N-1: P2→SR-1 … P6→SR-5).
SKILLS: security-review-incremental, security-audit-log.
SCOPE: review ONLY the code added or changed since the last approved tag: `git diff <last>..HEAD` (list the files reviewed). We just finished building: <phase name and what was built, including UI and backend changes>.

Check each item specifically, using the CareCast applicability decisions in TRD §9.3 (INC-01…INC-10). For each item report: APPLICABLE or NOT APPLICABLE (with reason and the verification you ran), then PASS / FAIL / N/A, the evidence (command + raw output or file:line), and any finding.
(1) INC-01 Permission checks on every endpoint — authentication (is the user logged in?) and authorization (are they allowed this resource?). CareCast decision D-04: no accounts. VERIFY: no state-changing or per-user endpoint exists; E8 is stateless. If that is false, it becomes REQUIRED — stop and ask me.
(2) INC-02 Hard-coded secrets, API keys or tokens (scan the diff and history).
(3) INC-03 User input validated on the BACKEND, not just the frontend.
(4) INC-04 Error messages safe — no stack traces, file paths or database details.
(5) INC-05 User-generated content sanitised before storing or displaying (CareCast stores none; check rendering sinks and URL/hash params).
(6) INC-06 Database queries parameterised, not string concatenation.
(7) INC-07 File uploads validated and stored securely (verify none exist: no multipart routes).
(8) INC-08 Rate limiting on endpoints that could be abused.
(9) INC-09 CSRF in state-changing operations (verify: no cookies/sessions; E8 only computes).
(10) INC-10 Sensitive data encrypted and not over-exposed in API responses.

THEN: flag EVERYTHING you find; FIX confirmed vulnerabilities (security only); re-run the relevant tests; and tell me what you changed and why. Functional (non-security) bugs outside this phase's scope: do NOT fix — add to reports/known-issues.md.
If a UI exists, include real screenshots of the current UI and status (verified file paths) under the relevant section; if not, state "no UI at this phase" and attach the terminal/test evidence instead.
OUTPUT FORMAT: a table of the 10 items (status, finding, fix, validation, evidence) + "What I changed and why" + residual risks. Do not invent findings or results. STOP.
````

### 6.3 PL — Pre-launch review (adapts Master Prompt #2; run once in Phase 7)

````text
Apply G-0. PRE-LAUNCH SECURITY REVIEW (run once, in Phase 7) → output reports/security/PL.md.
SKILLS: security-review-prelaunch, security-audit-log.
SCOPE: the ENTIRE codebase and the deployment configuration. Use TRD §9.3 (PL-01…PL-13) for the CareCast applicability decisions; verify each decision still holds.
For each item give PASS / FAIL / NOT APPLICABLE (with reason and the verification you ran) and evidence (command + raw output or file:line):
(1) PL-01 All secrets are in environment variables, not in code (scan repo + history).
(2) PL-02 All user input is validated on the backend.
(3) PL-03 All database queries use parameterised queries (run AT-05).
(4) PL-04 All API endpoints have authentication and authorization checks (CareCast: NOT APPLICABLE per D-04 — re-verify no write/per-user endpoint exists).
(5) PL-05 Error messages don't expose internal details.
(6) PL-06 CORS is locked to my domain only (CareCast: same-origin; verify NO Access-Control-* headers; if the UI is hosted elsewhere allow exactly that origin).
(7) PL-07 Debug mode is off (CARECAST_ENV=prod; docs/openapi 404; no reload).
(8) PL-08 All cookies have secure, httpOnly and sameSite flags (CareCast sets none — verify no Set-Cookie).
(9) PL-09 HTTPS is enforced everywhere (deployment-dependent; local HTTP = NOT APPLICABLE with reason; deployed = redirect + HSTS).
(10) PL-10 Rate limiting in place on login and sensitive endpoints (no login; limiter on /api/* and E8).
(11) PL-11 File uploads validated and stored securely (verify none exist).
(12) PL-12 Dependencies have no known critical vulnerabilities (pip-audit raw output + vendored JS advisory check).
(13) PL-13 No test credentials, dummy data or development artifacts remain (fixtures excluded from prod image; DB only real CDC data; placeholders labelled; .gitignore audit).
Give me a pass/fail for each item and FIX anything that FAILS (security only), re-validate, and record the actual outcome. Mark irrelevant controls NOT APPLICABLE with reasons instead of adding infrastructure. Do not invent results. STOP.
````

### 6.4 Secret-scan & dependency commands (use inside the reviews; paste real output)

````text
git grep -nEi "(api[_-]?key|secret|token|passwd|password|bearer|private[_-]?key)" -- . ":(exclude)docs" ":(exclude)reports"
git log -p --all -S"password" --oneline | head
python -m pip_audit -r requirements.txt
python -m bandit -r carecast -q            # optional, dev-only
python -m pytest tests/unit/test_sql_guard.py -q   # AT-05
````

---

## 7. Final audit prompts (Phase 7)

### FA-1 — Genuine screenshots

````text
Apply G-0. Capture GENUINE screenshots of the current UI and project status.
1. Start the app in prod mode with the real database (CARECAST_ENV=prod). Save the server command and its startup output.
2. Run scripts/capture_screenshots.py. Capture S1–S6 at 1280 px (and 375 px) into reports/screenshots/ using the naming <phase>-<screen>-<width>.png.
3. Capture status evidence as TEXT logs (not images) in reports/logs/: pytest summary, scripts/verify.py output, pip-audit output, API health JSON, prod-mode header check.
4. Verify every screenshot: file exists; `ls -l`; `sha256sum`; pixel dimensions; open it and confirm it shows the intended screen. Record all in the screenshot register of docs/FINAL_PROJECT_AUDIT.md §13.
5. NEVER create images by drawing, mocking or editing; if a screenshot cannot be captured, write "NOT CAPTURED — <reason>".
STOP.
````

### FA-2 — Populate the audit (facts only)

````text
Apply G-0. Populate docs/FINAL_PROJECT_AUDIT.md.
RULES: use ONLY what is recorded in reports/ (phase reports, security reviews, logs, screenshots, known-issues). Do not add new analyses, new findings or new claims. Leave "NOT RUN" where nothing was run. Quote raw results. Do not remove any section or any verbatim prompt text.
1. Fill every table; keep the status vocabulary: PASS / FAIL / NOT APPLICABLE / NOT RUN / BLOCKED.
2. Embed each screenshot under the prompt/review it belongs to (path relative to docs/: ../reports/screenshots/<file>.png) AND list it in §13.
3. Paste the "What I changed and why" text of each security review verbatim.
4. Fill the debugging history from the phase reports (every failure that really occurred).
5. At the end give a "consistency check": list any place where the audit and the phase reports disagree, or write "none found".
STOP.
````

### FA-3 — Frontend vs backend + project health (flag, don't fix)

````text
Apply G-0. Answer two questions with evidence, then STOP.
Q1. Did our frontend changes disturb the backend functionality? Compare: the backend test results and the OpenAPI snapshot sha256 before P5, after P5, after P6; run every endpoint E1–E8 against the real DB and compare with the contracts; list commits that touched backend files during P5–P6 (expected: none). Answer YES/NO with evidence.
Q2. Is the project working properly, without errors, after the master reviews? Run: full tests, E2E, scripts/verify.py, start the app in prod mode and click through S1–S6 with the console open (record console errors/warnings and CSP violations), check the logs for exceptions.
If ANY error is found: DO NOT FIX IT. For each, record: ID, where, symptom, raw evidence, severity (Critical/High/Medium/Low), likely cause (hypothesis, marked as such), recommended fix. Put them in docs/FINAL_PROJECT_AUDIT.md §11 with status "FLAGGED — not fixed".
(Exception: confirmed SECURITY vulnerabilities are fixed under the PL review, not here.)
STOP.
````

---

## 8. Approval message templates (you → agent)

````text
APPROVED: PHASE 1
````
````text
APPROVED: PHASE 2
Decisions: OD-03 target = <count | rate>, diseases = <flu, covid19, rsv — or subset>; OD-06 training_start = <YYYY-MM-DD>.
````
````text
APPROVED: PHASE 3
````
````text
APPROVED: PHASE 4
````
````text
APPROVED: PHASE 5
````
````text
APPROVED: PHASE 6
Decisions: OD-05 — do not attempt F13; OD-04 — deployment = <local | Docker | free-tier PaaS: name>.
````
````text
APPROVED: PHASE 7
````
````text
NOT APPROVED: PHASE <N>
Reason: <what must change>. Fix the current phase only, re-run validation, and report again.
````
