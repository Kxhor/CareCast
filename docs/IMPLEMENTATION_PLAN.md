# IMPLEMENTATION_PLAN — Seven Sequential Phases with Approval Gates

| Field | Value |
|---|---|
| Document | `docs/IMPLEMENTATION_PLAN.md` (6 of 8) |
| Version / status | 1.0 — **DRAFT FOR USER APPROVAL** |
| Date | 10 Oct 2026 |
| Depends on | [PRD](PRD.md) · [TRD](TRD.md) · [APP_FLOW](APP_FLOW.md) · [UI_UX_DESIGN](UI_UX_DESIGN.md) · [BACKEND_SCHEMA](BACKEND_SCHEMA.md) |
| Executor | Antigravity agent, using prompts in [ANTIGRAVITY_PROMPTS](ANTIGRAVITY_PROMPTS.md) |

---

## 1. Operating rules (apply to every phase)

1. **One phase at a time.** Do not begin phase *N+1* until the user replies exactly **`APPROVED: PHASE N`**.
2. **Inspect first.** At the start of every phase: read the docs listed for that phase, run `git status`, list the repo, and report what already exists before changing anything.
3. **Skills (per `GLOBAL_SKILLS_REPORT.md`, auto-triggered; named here so they are applied deliberately):**
   - *Superpowers:* `brainstorming` before planning a phase, `test-driven-development` for logic, `systematic-debugging` on any failure, `verification-before-completion` before declaring done.
   - *Ponytail:* every diff passes the 7-rung ladder (YAGNI → reuse → stdlib → platform → installed package → one line → minimum code). **No new dependency without approval.**
   - *Matt Pocock skills:* `domain-modeling`, `codebase-design` for P2–P4; `diagnosing-bugs` on failures.
   - *Taste Skill + Impeccable:* P5–P6 UI work (Design Read, dials, anti-slop, a11y/UX polish).
   - *Security Review:* `security-review-incremental` after P2–P6; `security-review-prelaunch` in P7; `security-audit-log` for records.
4. **Evidence, not claims.** Every validation result must be pasted from a real command run and saved to `reports/logs/`. Never fabricate, estimate, or "expect" results.
5. **No silent changes.** Material scope, architecture, or dependency changes require user approval (record in the phase report under "Deviations").
6. **No mock substitution.** Hard-coded demo numbers may not replace required functionality (AT-31).
7. **Failure protocol.** If validation fails: *fix within the current phase → rerun the relevant checks → report the failure and the fix*. Use the recovery prompts (RV-n). Never mark a phase complete with failing required checks.
8. **Security fixes vs functional bugs.** Confirmed security vulnerabilities are fixed and re-validated. Unrelated functional defects found **during the final audit** are *documented and recommended, not silently fixed* (P7).
9. **Reports.** End every phase with `reports/phase-N.md` (template in §3) and, for P2–P6, `reports/security/SR-n.md`.
10. **Approval gate.** The agent stops after the phase report and waits.

### 1.1 Sequence & dependencies

```
P1 Setup ─▶ P2 Data+DB ─▶ P3 Forecast engine ─▶ P4 API+planning ─▶ P5 Frontend ─▶ P6 Polish/a11y ─▶ P7 Test+Pre-launch+Deploy+Audit
              │SR-1          │SR-2                │SR-3              │SR-4 +R1       │SR-5 +R2          │PL + final audit
```
No phase may start before its predecessor is approved. Authentication phase: **not required** (D-04) — recorded here so the omission is explicit.

### 1.2 Relative size (no hour promises)
P1 S · P2 M · P3 L · P4 M · P5 L · P6 M · P7 M.

---

## 2. Feature ↔ phase ↔ test map (compact traceability; full matrix in [PRD §12](PRD.md))

| Feature | P1 | P2 | P3 | P4 | P5 | P6 | P7 |
|---|---|---|---|---|---|---|---|
| F1 Ingestion | | ● | | | | | re-verify |
| F2 History | | | | ● API | ● UI | | |
| F3 Forecast | | | ● | ● API | ● UI | | |
| F4 Evaluation | | | ● | ● API | ● UI | | |
| F5 Alert | | | | ● | ● | | |
| F6 Explain | | | ● | ● | ● | | |
| F7 What-if | | | | ● | ● | | |
| F8 Capacity | | | | ● | ● | | |
| F9 Actions | | | | ● | ● | | |
| F10 Provenance | | | | ● | ● | | |
| F11 Overview | | | | ● | ● | ● | |
| F12 Disease select | | | ● | | ● | | |
| Security | | SR-1 | SR-2 | SR-3 | SR-4 | SR-5 | PL |

---

## 3. Phase report template (`reports/phase-N.md`)

```
# Phase N report — <title>
Date/time start–end · Commit(s) · Skills applied
1. Repo state found at start (git status, existing files)
2. Docs read (list)
3. What was built (files created/changed)
4. Validation: command → raw output excerpt → PASS/FAIL (link to reports/logs/…)
5. Acceptance criteria table (ID → result → evidence)
6. Failures encountered, root cause, fix, re-validation
7. Deviations / approvals requested (scope, architecture, dependencies)
8. Security review summary (link to reports/security/SR-n.md)
9. Open issues / risks
10. Screenshots (verified paths) if a UI exists
11. STOP — awaiting "APPROVED: PHASE N"
```

---

## 4. Phases

### P1 — Project setup & repository audit
| | |
|---|---|
| **Objective** | Create a clean, reproducible skeleton and inspect any existing repo contents before touching anything. |
| **Features** | none (foundation) |
| **Depends on** | User approval of the eight docs (OD-01, OD-02, OD-07) |
| **Read first** | All eight docs, `GLOBAL_SKILLS_REPORT.md`, `Master_security_prompts.txt` |
| **Deliverables** | Repo audit (`reports/phase-1.md` §1); folder layout per TRD §13 (empty modules with docstrings only); `requirements.txt` / `requirements-dev.txt` with **exact pinned versions** from a real install; `.gitignore` (venv, `.env`, `data/raw/`, `data/*.db`, `reports/screenshots` optional, caches), `.dockerignore`, `.env.example` (variables from TRD §8); `carecast/settings.py` (env + TOML loader with validation); `carecast/db.py` (rw/ro connections, migration runner stub); `pyproject.toml` or pytest config; one smoke test; `scripts/verify.py` skeleton; `README.md` (setup + commands) |
| **Validation** | `python -m venv .venv` + `pip install -r requirements-dev.txt` from clean · `python -m pytest -q` · `python -c "import carecast"` · secret scan (`git grep -nEi "api[_-]?key|secret|token|password"` → none) |
| **Acceptance (measurable)** | (a) Clean-venv install succeeds; (b) smoke test passes; (c) `settings.py` raises a clear error on an invalid env value (unit test); (d) `.gitignore` excludes `.env`, `data/raw/`, `data/*.db`; (e) `pip-audit` runs and its output is saved (findings recorded, not hidden); (f) **zero dependencies beyond TRD §3.2** |
| **Security review** | Light check only (secrets, `.gitignore`). No SR file required. |
| **Gate** | `APPROVED: PHASE 1` |

### P2 — Data acquisition, validation & database
| | |
|---|---|
| **Objective** | Load real CDC data into SQLite with validation, and settle the **data decision** (target, diseases, training start). |
| **Features** | F1 |
| **Depends on** | P1 |
| **Read first** | PRD §2.4–2.5, BACKEND_SCHEMA (all), TRD §5.1 |
| **Deliverables** | `migrations/0001_core_data.sql`, `0002_forecasting.sql` (verbatim from BACKEND_SCHEMA); migration runner; `config/dataset_mapping.toml` **filled from real headers**; `ingest.py`, `quality.py`, `pipeline.py` (`migrate`, `ingest`, `check`); `data/README.md` (URLs, retrieval dates, SHA-256, licence/terms found); **Data Decision Record** in `reports/phase-2.md`: headers found, chosen target (count/rate), diseases that qualify, EDA plots/tables per disease (seasonality, zeros, regime breaks, coverage), proposed `training_start` |
| **Manual step (user)** | If the agent has no network: download the CSV(s) from `data.cdc.gov` (ids in PRD §2.5), place in `data/raw/`, and tell the agent the filenames |
| **Validation** | `pytest tests/unit/test_ingest.py tests/unit/test_quality.py tests/unit/test_schema.py` · `python -m carecast.pipeline migrate && ingest && check` · re-run `ingest` (0 new rows) · `sqlite3`/Python query counts vs CSV |
| **Acceptance (measurable)** | **AT-01, AT-02, AT-03, AT-04, AT-05, AT-45** pass · row count in T5 = filtered CSV row count (numbers shown) · every defect fixture is detected · DB `CHECK` rejects a non-Saturday date and a train/valid/test overlap (negative tests) · Data Decision Record present with raw evidence |
| **Security review** | **SR-1** on ingest/DB code (path handling, SQL, CSV parsing, error messages) |
| **Gate** | User decides **OD-03** (target) and **OD-06** (training start) in the approval message: `APPROVED: PHASE 2` + decisions |

### P3 — Forecast engine & evaluation
| | |
|---|---|
| **Objective** | Leak-free, reproducible forecasts with honest baseline comparison and explainability, persisted to the DB. |
| **Features** | F3, F4, F6, F12 (series availability) |
| **Depends on** | P2 (approved data decision) |
| **Read first** | TRD §5, PRD F3–F6, BACKEND_SCHEMA T7–T11 |
| **Deliverables** | `features.py`, `models.py`, `evaluate.py`, `explain.py`, `pipeline.py train`; `config/pipeline.toml`; persisted runs for each **available** disease; `reports/phase-3.md` with per-disease tables: split dates/sizes, MAE/RMSE per model × horizon × split, selected model, `beats_persistence`, interval coverage, top contributions — **raw numbers only, no thresholds applied** |
| **Method guardrails** | Chronological 60/20/20 on target weeks; walk-forward; selection on validation only; intervals from validation residuals; seed fixed; negative preds clipped and noted; no pickle/joblib persistence |
| **Validation** | `pytest tests/unit -q` (features, models, evaluate, explain) · `python -m carecast.pipeline train` twice and diff the metrics (identical) · leakage test |
| **Acceptance (measurable)** | **AT-08, AT-10 (storage), AT-11, AT-12, AT-13, AT-14 (logic), AT-18, AT-43** pass · DB `CHECK`s accept every stored run · all four models present per horizon (seasonal-naive only if history allows — then documented) · if the model does **not** beat persistence, the report says so and nothing is tuned on the test block |
| **Security review** | **SR-2** (no pickle/eval; file paths; numeric edge cases; deterministic seeds) — many items N/A with reasons |
| **Gate** | `APPROVED: PHASE 3` |

### P4 — Backend API & planning logic
| | |
|---|---|
| **Objective** | Read-only JSON API (E1–E8) with pure planning functions and a hardened HTTP layer. |
| **Features** | F2 (API), F3 (API), F4 (API), F5, F6 (API), F7, F8, F9, F10, F11 (API) |
| **Depends on** | P3 |
| **Read first** | BACKEND_SCHEMA §7–§10, TRD §6, §9 |
| **Deliverables** | `planning.py` (pure functions), `api/{main,routes,schemas,ratelimit}.py`, `config/planning.toml` (placeholders **clearly labelled**, limitations text from PRD §9, action checklists), security middleware (headers, body cap, rate limit, generic errors), docs/openapi disabled in prod, static mount for `web/` (serving a placeholder page), OpenAPI contract snapshot `tests/contract/openapi.snapshot.json`, API tests |
| **Validation** | `pytest tests/unit/test_planning.py tests/api -q` · manual `curl` of every endpoint against the real DB (outputs saved) · header inspection · forced-error test |
| **Acceptance (measurable)** | **AT-06, AT-09, AT-10 (API), AT-15, AT-16, AT-19, AT-21, AT-22, AT-24, AT-25 (API), AT-26, AT-28, AT-30, AT-33, AT-34, AT-35, AT-37** pass · every endpoint's response validates against its Pydantic model · tier boundary table passes · DB opened read-only (write attempt fails in a test) |
| **Security review** | **SR-3** (full 10-item review on all new API code) |
| **Gate** | `APPROVED: PHASE 4` |

### P5 — Frontend core build
| | |
|---|---|
| **Objective** | Implement S1–S6 against the real API following UI_UX_DESIGN and APP_FLOW. |
| **Features** | F2, F3, F4, F5, F6, F7, F8, F9, F10, F11, F12 (UI) |
| **Depends on** | P4 |
| **Read first** | UI_UX_DESIGN (all), APP_FLOW (all), TRD §7 |
| **Deliverables** | `web/` (tokens, base, layout, components CSS; ES-module JS; icons sprite; vendored Chart.js with `VERSIONS.md` + SHA-256 + licence); all six routes; all states in APP_FLOW §5; Playwright E2E tests; honesty markers (badges, disclaimers) |
| **Design process** | Taste Skill **Design Read** + dials, Impeccable *Operate* mode for S1–S5, *Read* for S6 (UI_UX_DESIGN §5) |
| **Validation** | `pytest -q` (backend unchanged) · `pytest tests/e2e -q` · contract-snapshot diff · grep for forbidden DOM sinks |
| **Acceptance (measurable)** | **AT-07, AT-14 (E2E), AT-17, AT-20, AT-23, AT-25 (E2E), AT-27, AT-29, AT-31, AT-32, AT-38, AT-47 (R1)** pass · no console errors on any route · CSP violations = 0 (or documented and approved) · no `innerHTML`-family usage with API data |
| **Security review** | **SR-4** (XSS, CSP, URL params, localStorage, dependency vendoring) |
| **Regression R1** | Run the full backend suite **before** and **after** P5; compare results and the OpenAPI snapshot hash; any difference ⇒ explain (this answers "did frontend changes disturb backend?") |
| **Gate** | `APPROVED: PHASE 5` |

### P6 — UI polish, accessibility & responsive fidelity
| | |
|---|---|
| **Objective** | Match the reference identity, meet the a11y checklist, work on all breakpoints. |
| **Features** | F11 (polish), cross-cutting UX |
| **Depends on** | P5 |
| **Read first** | UI_UX_DESIGN §1–§3, §6, §9, §10 |
| **Deliverables** | CSS/JS refinements only (**no backend changes**), `scripts/capture_screenshots.py`, screenshots at 320/375/768/1280/1440 for each screen in `reports/screenshots/`, a11y checklist results with evidence, VC-01…VC-16 side-by-side review |
| **Validation** | E2E at breakpoints · a11y checklist run (manual + Lighthouse record) · screenshot verification (`ls -l`, `sha256sum`, dimensions) |
| **Acceptance (measurable)** | **AT-40, AT-41, AT-42, AT-47 (R2)** pass · every VC item has pass/fail + screenshot · deviations listed with reason |
| **Security review** | **SR-5** (only the polish diff) |
| **Regression R2** | As R1 (backend suite + contract hash identical) |
| **Gate** | `APPROVED: PHASE 6` + decisions **OD-05** (F13: attempt or not) and **OD-04** (deployment target, needed at the start of P7) |

### P7 — Testing hardening, pre-launch security review, deployment & final audit
| | |
|---|---|
| **Objective** | Prove the whole system works from a clean clone, run the comprehensive security review, deploy (per OD-04), and populate the final audit with **actual** findings. |
| **Features** | all (verification) |
| **Depends on** | P6 |
| **Read first** | TRD §9.3, §10, §12 · FINAL_PROJECT_AUDIT · `Master_security_prompts.txt` |
| **Deliverables** | `scripts/verify.py` complete; Dockerfile (non-root, no dev deps, no fixtures) if OD-04 includes Docker; deployment notes; **Pre-launch review** `reports/security/PL.md` (13 items PASS / FAIL / NOT APPLICABLE with reasons; fixes for failures); populated `docs/FINAL_PROJECT_AUDIT.md`; screenshots embedded |
| **Validation** | Fresh clone → install → `python -m carecast.pipeline rebuild` → `python scripts/verify.py` · `pip-audit` · prod-mode checks (docs 404, no CORS/cookies, headers) · container run + health check (if Docker) |
| **Acceptance (measurable)** | **AT-05, AT-33, AT-36, AT-37, AT-39, AT-43, AT-44, AT-45** pass · PL-01…13 each have a recorded status · all failing PL items fixed and re-validated, or explicitly blocked with reason · audit contains **only** observed facts |
| **Final-audit rule** | Fix security vulnerabilities. For **unrelated functional errors** found during the audit: **do not fix** — record symptom, evidence, severity, and a recommended fix |
| **Gate** | `APPROVED: PHASE 7` → project complete |

---

## 5. Acceptance-test ownership summary

| Phase | ATs that must pass at its gate |
|---|---|
| P1 | (setup checks) |
| P2 | AT-01, 02, 03, 04, 05, 45 |
| P3 | AT-08, 10*, 11, 12, 13, 14*, 18, 43 |
| P4 | AT-06, 09, 10, 15, 16, 19, 21, 22, 24, 25*, 26, 28, 30, 33, 34, 35, 37 |
| P5 | AT-07, 14, 17, 20, 23, 25, 27, 29, 31, 32, 38, 47 |
| P6 | AT-40, 41, 42, 47 |
| P7 | AT-05, 33, 36, 37, 39, 43, 44, 45 (+ full regression of all earlier ATs) |
| — | AT-46 deferred (F13) |

`*` = partially covered in that phase (storage/logic or API/E2E halves).

---

## 6. Gate checklist (the agent must paste this, filled, at the end of every phase)

```
[ ] Docs read and listed          [ ] Repo state reported before changes
[ ] Only this phase's scope built [ ] No new dependency (or approval requested)
[ ] Every AT for this phase run   [ ] Raw outputs saved in reports/logs/
[ ] Failures documented + fixed   [ ] Security review done (SR-n) or N/A stated
[ ] No fabricated numbers         [ ] Deviations listed
[ ] STOPPED and waiting for "APPROVED: PHASE N"
```

---

## 7. Risks to schedule (from PRD §8) and phase where they are checked
R-01/R-02/R-04 → P2 · R-03/R-05 → P3 · R-09/R-10 → P4/P5 · R-11 → P5 · R-12 → P6 · R-13/R-08 → P7 · R-06/R-07 → every gate.
