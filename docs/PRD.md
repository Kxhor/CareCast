# PRD — CareCast: Explainable Respiratory-Admission Forecasting & Capacity Early-Warning

| Field | Value |
|---|---|
| Document | `docs/PRD.md` (1 of 8) |
| Version / status | 1.0 — **DRAFT FOR USER APPROVAL** |
| Date | 10 Oct 2026 |
| Project type | College project — decision-support prototype (not a clinical system) |
| Companion docs | [TRD](TRD.md) · [APP_FLOW](APP_FLOW.md) · [UI_UX_DESIGN](UI_UX_DESIGN.md) · [BACKEND_SCHEMA](BACKEND_SCHEMA.md) · [IMPLEMENTATION_PLAN](IMPLEMENTATION_PLAN.md) · [ANTIGRAVITY_PROMPTS](ANTIGRAVITY_PROMPTS.md) · [FINAL_PROJECT_AUDIT](FINAL_PROJECT_AUDIT.md) |

## 0. How to read this document

### 0.1 Evidence labels (used in every document)

| Label | Meaning |
|---|---|
| ✅ **VERIFIED** | Confirmed directly from a provided file/image, or by a web search I ran for this task (source noted). |
| 📄 **REPORTED** | Stated in an attached research report. Not independently verified by me. |
| 🧪 **ASSUMPTION** | A design parameter or planning assumption. Configurable. **Not** a validated rule. |
| 💡 **RECOMMENDATION** | My proposed decision, with a justification. |
| ⚠️ **TO-VERIFY** | Cannot be confirmed from here. A named phase must confirm it before anything depends on it. |

### 0.2 ID registry (identical in all eight documents)

| Prefix | Meaning | Range |
|---|---|---|
| F | Feature | F1–F13 |
| S | Screen | S1–S6 |
| E | API endpoint | E1–E8 |
| T | Database table | T1–T11 |
| P | Implementation phase | P1–P7 |
| AT | Acceptance test | AT-01–AT-47 |
| D | Architecture/product decision | D-01–D-10 |
| A | Assumption | A-01–A-13 |
| R | Risk | R-01–R-14 |
| L | User-visible limitation | L-01–L-12 |
| OD | Open decision needing user approval | OD-01–OD-07 |
| SR / PL | Incremental / pre-launch security review | SR-1–SR-5, PL (items INC-01–10, PL-01–13) |
| X | Contradiction between reports (§2.4) | X-01–X-13 |
| C | UI component (UI_UX_DESIGN §4) | C-01–C-23 |
| A11Y | Accessibility checklist item | A11Y-01–A11Y-14 |
| VC | Visual acceptance criterion | VC-01–VC-16 |

---

## 1. Executive summary

**Problem (from the brief).** Hospitals allocate beds, staff and supplies reactively because demand is hard to predict (seasons, outbreaks, demographics, emergencies). COVID-19 exposed the cost of reactive planning.

**What the evidence says.** All three attached reports independently reach the same conclusion: the eight-module solution idea is **too broad for a college project**. Build **one validated, explainable forecasting workflow** and be honest about what it cannot claim.

**Product (D-01).** **CareCast** forecasts **weekly U.S. hospital respiratory admissions** (influenza, COVID-19, RSV; national level) from CDC/NHSN public data. It then:

1. compares the forecast with a **configurable planning threshold** and raises a three-tier early-warning (Normal / Watch / Elevated);
2. **explains** what drove the forecast (additive linear contributions + permutation importance);
3. lets the user run **what-if surge scenarios**;
4. offers an **assumption-based, clearly SIMULATED capacity illustration** (beds, nurses);
5. shows **model-vs-baseline evidence** and **data provenance & limitations** on every screen.

**What it is not.** Not a diagnostic or clinical tool. Not validated for any individual hospital. Not a bed-occupancy predictor. Demonstration forecasts are **not clinically validated**.

---

## 2. Research & evidence synthesis

### 2.1 Attachment inventory (missing / unreadable check)

| # | File | Status | Notes |
|---|---|---|---|
| 1 | `Perplexity_Reports_for_healh.md` ("Report A") | ✅ Readable (502 lines) | Citations appear as unresolved markers `[web:1]`; no URL list preserved. |
| 2 | `Healthcare_Analysis.md` ("Report B") | ✅ Readable (1,132 lines) | ChatGPT export. Contains render-markup (`<box>`, `<Cite refs=…/>`); cited sources are not recoverable from the file. |
| 3 | `Healthcare_Resource_Optimization.md` ("Report C") | ✅ Readable (979 lines) | ChatGPT export (3 turns). The "Minimal starter code" heading has **no code block** (lost in export). |
| 4 | `Reference_Ui.jpg` | ✅ Readable (736×837 px) | Screenshot of the third-party "Apollo admin 2024" template. Down-scaled; exact px sizes are unknown (see UI doc). |
| 5 | `GLOBAL_SKILLS_REPORT.md` | ✅ Readable | Describes six installed Antigravity skill frameworks. |
| 6 | `Master_security_prompts.txt` | ✅ Readable | Two master prompts + instructions for a final verification file. |
| — | **Raw dataset file** | ❌ **Not attached** | No CSV was provided. Column names are therefore **⚠️ TO-VERIFY in P2**. |

> Three of the six files were not in my initial context and were read from disk. No attachment was unreadable.

### 2.2 Individual analysis

#### Report A — "CareCast" (Perplexity-style project brief)

| Aspect | Content |
|---|---|
| **Key findings** | MVP = forecast near-term respiratory admissions → compare to configurable threshold → alert → explain → what-if. Decision support only. Keep *admissions*, *occupancy*, *capacity* separate. |
| **Datasets** | CDC "Weekly Hospital Respiratory Admission Levels and Rates by Jurisdiction" (NHSN). Proposes target `totalConfFluNewAdm` (weekly flu admissions, national). |
| **Algorithms** | Baseline ŷₜ₊₁ = yₜ. Linear Regression on lags (1, 2, 4 wks), week, month, rolling mean. Later: RandomForest, GradientBoosting, XGBoost, SARIMA. 80/20 chronological split. MAE (+RMSE, careful MAPE). SHAP if time. |
| **Stack** | Python, pandas, scikit-learn, Plotly, Streamlit, CSV storage. "No backend/auth/database needed." |
| **Sources** | `[web:1]` only (unresolved). |
| **Limitations stated** | U.S. data; respiratory only; admissions ≠ occupancy; coverage varies; thresholds are planning assumptions. |
| **Weak points** | (a) Internal inconsistency: binary risk flag (High/Normal) vs a three-level dashboard status. (b) Claims specific column names that I could not verify. (c) 80/20 split leaves no validation block for model selection. |
| **Implications** | Gives the strongest, most defensible narrative. Adopted as the **spine** of the MVP. |

#### Report B — "Healthcare Analysis" (8-factor hackathon analysis, verdict 🟡 Yellow Light)

| Aspect | Content |
|---|---|
| **Key findings** | Don't build eight disconnected modules. Build one demand-to-decision flow: forecast → bed demand → shortage alert → staffing recommendation → explainability → what-if "digital twin". Biggest risk: access to real operational data. |
| **Datasets** | Option A Synthea (synthetic), B MIMIC-IV (credentialed), C eICU (credentialed), D CMS public hospital data, E India HMIS. Recommends a **self-generated synthetic daily operational dataset** (department × date). |
| **Algorithms** | Seasonal-naive baseline; Random Forest / `HistGradientBoostingRegressor`; statsmodels; optional OR-Tools; uncertainty intervals; chronological train/val/test; interval-coverage check. |
| **Competitors (vendor-described)** | Epic Hospital Patient Flow, Qventus, LeanTaaS iQueue, TeleTracking Operations IQ. |
| **Research cited** | Three 2025–2026 reviews (ED admission prediction; ED demand prediction; AI for resource allocation). |
| **Limitations stated** | Synthetic data can't establish real accuracy; admissions ≠ beds; feature importance ≠ causation. |
| **Weak points** | (a) Cited reviews are unverified (see 2.6). (b) Recommends synthetic data while A and C recommend real public data. (c) Daily synthetic data invites fabricated-looking results. |
| **Implications** | Supplies the **forecast-to-action** idea (→ F5, F7, F8, F9), the **interval-aware** thinking, and the **red-flag list** used in the audit. Its synthetic-data route is **not adopted** (D-02). |

#### Report C — "Healthcare Resource Optimization" (hackathon-assistant chat, 3 turns)

| Aspect | Content |
|---|---|
| **Key findings** | Priority tiers: **P0** (report's own tier label) admission forecasting, bed/capacity alerts, explainability; **P1** staffing, inventory; **P2** ICU, epidemic, real-time optimisation. *(These P-labels are Report C's tiers, not the project phases P1–P7.)* Recommended "Option A": demand early-warning system. |
| **Datasets** | CDC weekly respiratory admissions (data.cdc.gov `vdzy-6i9v`), **target = admission rate**. MIMIC-IV flagged as slow to access. CDC FluView optional context. |
| **Algorithms** | Previous-week baseline; linear regression on lagged rates; chronological split; MAE; show uncertainty if feasible. |
| **Stack** | Streamlit + pandas + scikit-learn + Plotly. FastAPI/SQLite only if needed. |
| **Weak points** | (a) Mixes "7-day horizon" (daily) with weekly data. (b) Targets *rate* while A targets *count*. (c) Starter code lost in export. (d) 36-hour / 1–2-person framing differs from a college project. |
| **Implications** | Confirms the A-based MVP, supplies its own **priority tiers (labelled P0/P1/P2 in that report — not our phases)** and the evaluator checklist. |

### 2.3 Collective synthesis — convergence

All three reports agree on: **narrow scope**; **decision support, not clinical**; **separate admissions / occupancy / capacity**; **chronological validation**; **always beat-or-disclose a naive baseline**; **explainability + what-if as differentiators**; **no deep learning**; **label simulated content**; **no claim of lives saved**.

### 2.4 Contradictions and how this PRD resolves them

| # | Contradiction | Reports | Resolution (decision) |
|---|---|---|---|
| X-01 | Real weekly CDC data vs synthetic daily operational data | A, C vs B | **Real CDC data only** (D-02). No synthetic operational dataset. Only user-adjustable *assumptions* in F8 are simulated, and are labelled. |
| X-02 | Target = count vs rate | A vs C | Determined at the **P2 data gate** from the real headers (OD-03): prefer weekly new-admission **count**; fall back to **rate**. The UI states which one is used. |
| X-03 | Horizon: "next 7 days" vs 1–4 weeks | B, C vs A | **1–4 weeks**, weekly data. "Next 7 days" ≙ horizon 1. |
| X-04 | No backend (Streamlit) vs FastAPI/SQLite | A vs B, C | **FastAPI + SQLite + static web** (D-03). Reasons in TRD §3. Streamlit remains the documented fallback. |
| X-05 | Threshold-only vs bed/staff recommendations | A vs B | Both, **separated**: F5 threshold alert (data-driven) and F8 capacity illustration (assumption-driven, SIMULATED). |
| X-06 | Binary vs three-level alert | A (both) | **Three tiers** defined from the forecast interval (D-06). |
| X-07 | SHAP vs feature importance | A, C vs B | **Linear contributions + permutation importance** (no extra dependency). SHAP deferred (D-07). |
| X-08 | Baseline: persistence vs seasonal-naive vs "previous week" | A, C vs B | **Report both.** "Beats baseline" is judged against **persistence**; seasonal-naive is shown as an additional reference. |
| X-09 | Model menu (LR, RF, GB, XGBoost, SARIMA) | A, B, C | **Linear regression on lags + HistGradientBoosting** as the only comparator. XGBoost/SARIMA deferred (dependency-light). |
| X-10 | 80/20 vs train/val/test split | A vs B | **60/20/20 chronological walk-forward** (A-04) so model choice and intervals never touch the test block. |
| X-11 | Metrics: MAPE included? | A vs B, C | **MAE, RMSE, interval coverage.** MAPE excluded (off-season values near zero make it unstable). |
| X-12 | Time frame: 24–48 h hackathon vs college project | B, C | **Seven phases with approval gates**; no hour estimates are promised. |
| X-13 | Data lineage | A vs C | A cites the "Levels and Rates" dataset yet names *count* columns. C names the same dataset yet targets *rate*. Catalog text only mentions rates and levels ✅. **Both candidate datasets are inspected in P2** (§2.5). |

### 2.5 Candidate datasets and the data decision

| ID | Dataset | Verified facts | Role |
|---|---|---|---|
| **DS-1** | *Weekly Hospital Respiratory Admission Levels and Rates by Jurisdiction* (NHSN) — `data.cdc.gov` id `vdzy-6i9v` | ✅ Weekly admission **rates** and **levels** for COVID-19, influenza, RSV. One row = jurisdiction × week (Sun–Sat). Metrics reflect reporting hospitals and **may not represent all hospitals**. | Candidate for rate target and admission-level context. |
| **DS-2** | *Weekly Hospital Respiratory Data (HRD) Metrics by Jurisdiction* (NHSN) — id `ua7e-t2fy` | ✅ Aggregated counts since Aug 2020; metrics on capacity, occupancy, hospitalisations, **new admissions**, plus **reporting-coverage** metrics. **317 columns** in a 2025 snapshot. RSV was voluntary until 1 Nov 2024. | **Primary candidate** for count target + coverage feature. |
| DS-3 | Preliminary HRD (`mpgq-jmmr`) | ✅ Updates weekly on Wednesdays with preliminary data; DS-2 matches the Friday-published dashboards. | Not used (preliminary values get revised). |
| — | Older HHS hospital-metrics dataset | ✅ Archived; no updates after 1 Nov 2024. | Evidence that datasets get **archived** → R-08. |
| — | Synthea / MIMIC-IV / eICU / CMS / HMIS | 📄 Per Report B | **Not used** (D-02). |

**Verification method (important).** ✅ Facts above come from third-party catalog mirrors of CDC metadata (DataLumos, Baselight, Data Rescue Project) found via web search. I did **not** open `data.cdc.gov` itself, and the sandbox has no network. **Exact column names, value ranges, file size and licence terms are ⚠️ TO-VERIFY in P2.**

**Data decision rule (to be confirmed at the P2 gate, OD-03):**

1. Download DS-2; locate columns for weekly **new admissions** per disease, jurisdiction, week-ending date, and hospital-reporting coverage.
2. Download DS-1; locate **rate** and **level** columns.
3. Target = **weekly new-admission count** (national, per disease) if present in DS-2; else **admission rate** from DS-1. Record the choice, the mapping and the evidence in `data/README.md` and `config/dataset_mapping.toml`.
4. If a disease has insufficient valid history, **exclude that disease** (do not fabricate), and show the reason on S6.

### 2.6 External verification performed for this task

| Claim | Result |
|---|---|
| CDC NHSN datasets exist as described (DS-1/2/3) | ✅ Confirmed via catalog mirrors (see 2.5). |
| CDC coordinates weekly hospitalisation-admission forecasts based on this dataset | ✅ Stated in the DS-3 catalog text. **Implication:** CareCast replicates a public-health activity at student scale. It must **not** claim to outperform official forecasts. |
| Report B: "31 studies; 7 rigorous; AUROC 0.81–0.93" (PMID 40206990) | ⚠️ **Not found.** My search surfaced *different* reviews (e.g., *Healthcare Informatics Research* 2025: 20 studies). The numbers in Report B stay 📄 REPORTED and **must not be cited** as fact. |
| Report B: two 2026 reviews (ED demand; resource allocation) | ⚠️ Not independently checked. |
| Vendor capability claims (Epic, Qventus, LeanTaaS, TeleTracking) | 📄 Vendor-described only. |
| India DPDP Act 2023 / Rules 2025 relevance | 📄 Not needed: data are public, aggregate, de-identified. |

### 2.7 Practical implications for design

1. **Real, aggregate, public data** → no PII, no authentication, no uploads, smaller security surface.
2. **Few seasons of weekly history** → keep models simple and show uncertainty (R-05).
3. **Reporting-regime changes** (✅ mandatory reporting → voluntary → CMS-required; RSV voluntary until 1 Nov 2024) → structural breaks must be examined in EDA before choosing the training start (OD-06).
4. **Admissions ≠ occupancy** → capacity logic is split into a data-driven alert and a clearly simulated illustration.

---

## 3. Users and jobs-to-be-done

| User | Need | Primary features |
|---|---|---|
| **U1 Operations / capacity planner** (demo persona; no named person) | "What should we prepare for in the next 1–4 weeks, and how sure is the model?" | F3, F5, F6, F9, F11 |
| **U2 Public-health / system planner** | Compare disease trends; see surge sensitivity | F2, F7, F12 |
| **U3 Evaluator / faculty** | Judge rigour, honesty, usability, security | F4, F10, all screens |
| **U4 Developer (you)** | Reproduce results, extend later | F1, docs, tests |

Jobs-to-be-done: **J1** see next-4-week demand and its uncertainty; **J2** know when demand may exceed a planning line; **J3** understand *why*; **J4** stress-test with a surge; **J5** trust the model (baseline evidence); **J6** know the limits.

---

## 4. MVP selection and scope

### 4.1 Mapping of the eight "solution ideas" from the brief

| # | Solution idea | MVP status | Reason |
|---|---|---|---|
| 1 | Admission-volume forecasting | ✅ **IN (F1–F4, F12)** | Real data exists; suits time-series validation. |
| 2 | ICU bed-demand prediction | ❌ OUT | Needs ICU-specific acuity/LOS data. DS-2 *may* contain ICU occupancy columns ⚠️ TO-VERIFY → future extension only. |
| 3 | Staffing optimisation | 🟡 PARTIAL (F8) | Assumption-based nurse-per-shift **illustration**. No optimisation algorithm. |
| 4 | Inventory forecasting | ❌ OUT | No stock/consumption data. |
| 5 | Emergency / epidemic preparedness | 🟡 PARTIAL (F7, F9) | Surge **scenarios** and review actions. No outbreak prediction. |
| 6 | Patient-flow optimisation | ❌ OUT | No patient-movement data. |
| 7 | Dynamic reallocation recommendations | 🟡 PARTIAL (F9) | Rule-based **review checklist** by alert tier. Not live, not automated. |
| 8 | Explainable AI dashboard | ✅ **IN (F6, F4)** | Linear contributions + permutation importance. |

### 4.2 Feature list (MoSCoW)

| ID | Feature | Priority | One-line description |
|---|---|---|---|
| **F1** | Public-data ingestion & validation | Must | Load CDC CSV, validate, quality-check, store in SQLite. |
| **F2** | Historical demand explorer | Must | Trend chart + date-range filter. |
| **F3** | 1–4-week forecast with intervals | Must | Direct multi-horizon forecast + empirical 80 % interval. |
| **F4** | Baseline-vs-model evaluation | Must | Chronological walk-forward; MAE/RMSE/coverage; honest verdict. |
| **F5** | Capacity-pressure early-warning | Must | Configurable threshold; Normal/Watch/Elevated. |
| **F6** | Explainability | Must | Additive contributions, permutation importance, plain-language text. |
| **F7** | What-if surge simulator | Must | Scale forecast by a user-set % and re-evaluate the alert. |
| **F8** | Assumption-based capacity illustration | Should | Beds & nurses from user assumptions. **SIMULATED.** |
| **F9** | Recommended review actions | Should | Static, tier-based checklist (human review). |
| **F10** | Provenance, limitations & disclaimers | Must | Always-visible disclaimer + S6 detail. |
| **F11** | Planning dashboard overview | Must | KPI hero, watchlist, summary widgets. |
| **F12** | Disease selection | Should | Influenza (default), COVID-19, RSV. A disease is hidden if it fails data validation. |
| **F13** | State-level jurisdiction selector | Could | **Not in MVP.** Only if approved at the P6 gate (OD-05). |

### 4.3 Non-goals

Authentication · user accounts · patient-level data · hospital-specific bed prediction · ICU/inventory/patient-flow modules · live integrations (EHR, HL7/FHIR) · CSV upload by end users · deep learning · SHAP · clinical decision support · mobile app · multi-tenant hosting · any claim of improved outcomes.

---

## 5. Functional requirements

> Notation `F3.2` = feature F3, requirement 2. Each requirement maps to ≥1 acceptance test (§11).

### F1 — Ingestion & validation
- **F1.1** A CLI (`python -m carecast.pipeline ingest <csv>`) loads a CDC CSV using a **column-mapping file**; unmapped/missing required columns **abort** with a clear message.
- **F1.2** The raw CSV is **never modified**; its SHA-256 and row count are recorded.
- **F1.3** Dates are parsed to **Saturday week-ending**; non-Saturday dates are rejected.
- **F1.4** Checks: duplicate keys, missing weeks, negative counts, non-numeric values, coverage outside 0–100 %, unexpected jurisdiction/disease codes. Findings go to T6.
- **F1.5** Gaps ≤ 2 weeks may be linearly interpolated and **flagged** `is_imputed=1` (🧪 A-03b); longer gaps exclude the series.
- **F1.6** Ingestion is **idempotent** (re-running adds 0 rows).

### F2 — Historical explorer
- **F2.1** Line chart of weekly observations for the selected disease (national).
- **F2.2** Date-range filter; invalid ranges produce a clear empty/validation state.
- **F2.3** Imputed weeks are visually distinguishable.

### F3 — Forecast
- **F3.1** Horizons 1–4 weeks, **direct strategy** (one model per horizon).
- **F3.2** Each forecast has `point`, `lower`, `upper` (empirical 80 % interval from validation residuals, 🧪 A-05).
- **F3.3** Features at origin *t* use only data ≤ *t* (no leakage).
- **F3.4** Selected model per horizon is chosen on the **validation** block only.
- **F3.5** The forecast is regenerated by the offline pipeline, **never** in the request path.

### F4 — Evaluation
- **F4.1** Models: persistence baseline, seasonal-naive baseline (52-week lag when available), linear regression on lags, `HistGradientBoostingRegressor`.
- **F4.2** Walk-forward evaluation on validation and test blocks; metrics **MAE, RMSE**, plus **interval coverage** on test.
- **F4.3** UI verdict: "improves on baseline" **only if** test-block MAE of the selected model < persistence MAE; otherwise the UI says so plainly.
- **F4.4** No numeric pass/fail threshold is invented. Numbers are *reported*, not graded.
- **F4.5** Backtest series (actual vs predicted) are stored and plotted.

### F5 — Early-warning
- **F5.1** Default threshold per series = 75th percentile of the **training-block** values (🧪 A-06). The user may override.
- **F5.2** Tier rule (🧪 A-07), evaluated per target week:
  - **Elevated** if `point > threshold`
  - **Watch** if `point ≤ threshold < upper`
  - **Normal** if `upper ≤ threshold`
- **F5.3** Alerts are labelled "planning signal — not a bed-shortage prediction"; tier is conveyed by **text + icon + colour**.

### F6 — Explainability
- **F6.1** For the linear model: contribution of each feature = coefficient × (value − training mean); contributions + mean prediction = forecast (additive identity).
- **F6.2** For the tree model: permutation importance on the validation block.
- **F6.3** Plain-language text is **templated from stored numbers**, uses "associated with", never causal wording.

### F7 — What-if
- **F7.1** `surge_pct` ∈ [−50, +100] (🧪 A-09) scales point/lower/upper; alert recomputed.
- **F7.2** Output is labelled **"SCENARIO — not a prediction."**

### F8 — Capacity illustration (SIMULATED)
- **F8.1** User supplies: hospital typical weekly respiratory admissions, average length of stay (days), staffed beds, patients-per-nurse. Defaults are **demo placeholders** (🧪 A-08), not sourced data.
- **F8.2** Method (steady-state approximation, Little's law):
  - `relative_change = scenario_forecast / reference_level` (reference = mean of the last 4 observed weeks)
  - `hospital_weekly_admissions = typical_weekly_admissions × relative_change`
  - `est_occupied_beds = hospital_weekly_admissions × ALOS_days / 7`
  - `bed_gap = est_occupied_beds − staffed_beds`
  - `nurses_per_shift = est_occupied_beds / patients_per_nurse`
- **F8.3** API flag `is_simulated: true`; UI badge "SIMULATED — assumption-based".

### F9 — Review actions
- **F9.1** A static table maps tier → checklist (e.g., review projected discharges, staffing availability, respiratory-care supplies, surveillance trend). No dynamic recommendations.
- **F9.2** Each list ends with "Final decisions rest with authorised staff."

### F10 — Provenance & limitations
- **F10.1** Footer disclaimer on **every** screen.
- **F10.2** S6 shows source, dataset id, retrieval date, SHA-256, data-as-of, quality findings, L-01…L-12, model/eval summary.

### F11 — Overview
- **F11.1** All numbers come from the API (no hard-coded demo numbers).
- **F11.2** Widgets fail independently (partial-failure tolerance).

### F12 — Disease selection
- **F12.1** Changing disease re-queries and re-renders all widgets.
- **F12.2** Diseases failing validation are shown as "unavailable — reason".

### F13 — Jurisdiction selector (deferred)
- Reuse the same pipeline per state. Out of MVP.

---

## 6. Non-functional requirements

| ID | Area | Requirement |
|---|---|---|
| N1 | Security | See [TRD §9](TRD.md): validated inputs, parameterised SQL, read-only DB for API, generic errors, security headers, no secrets, rate limiting, XSS-safe rendering. |
| N2 | Reproducibility | Fixed seed; same raw file + code ⇒ identical metrics (AT-43). |
| N3 | Accessibility | WCAG 2.2 AA targets; keyboard operable; chart data tables. |
| N4 | Performance | **Measure and report** page-load and API timings. No invented pass/fail targets. |
| N5 | Maintainability | Few dependencies; no build step; typed Pydantic schemas; one module per concern. |
| N6 | Privacy | No patient-level fields anywhere (AT-45). |
| N7 | Cost | Free/open-source tools only; local-first. |
| N8 | Honesty | No fabricated results; simulated content labelled; unvalidated claims forbidden. |

---

## 7. Assumptions, constraints, dependencies

| ID | 🧪 Assumption |
|---|---|
| A-01 | Solo student + Antigravity agent; free tooling; Windows host (paths in skills report suggest Windows) — scripts must be cross-platform. |
| A-02 | Local-first. Public deployment is optional and decided at P7 (OD-04). |
| A-03 | National weekly history since Aug 2020 is long enough for baseline-comparable modelling ⚠️ TO-VERIFY. **A-03b:** gaps ≤ 2 weeks may be interpolated. |
| A-04 | Chronological split **60 % train / 20 % validation / 20 % test** (configurable). |
| A-05 | Prediction interval = 80 % central interval (10th–90th percentile) of validation residuals per horizon. |
| A-06 | Default planning threshold = 75th percentile of the training block. |
| A-07 | Tier rule uses the forecast interval upper bound (§F5.2). |
| A-08 | Capacity placeholders (typical weekly admissions, ALOS, staffed beds, patients-per-nurse) are **demo values, not data**. |
| A-09 | Scenario surge range −50 % … +100 %. |
| A-10 | Rate-limit defaults (e.g., 60 req/min/IP for GET, 20 req/min/IP for POST) are placeholders tuned in P4/P7. |
| A-11 | "Stale data" banner when `data_as_of` is more than 2 reporting weeks older than today. |
| A-12 | Python ≥ 3.11 and a Chromium-based browser (Playwright-managed) are available for tests/screenshots. |
| A-13 | The CDC datasets remain public; licence/terms are confirmed in P2 ⚠️ TO-VERIFY. |

---

## 8. Risk register

| ID | Risk | L / I | Mitigation |
|---|---|---|---|
| R-01 | CSV headers differ from reports' claims | High / High | Mapping file + abort-on-mismatch + P2 data gate (OD-03). |
| R-02 | Too few usable weeks/seasons for a disease | Med / High | Per-disease validation; hide failing disease (F12.2); keep baseline visible. |
| R-03 | Model does not beat persistence | Med / Med | Report it honestly (F4.3); UI wording handles both outcomes; recovery prompt in ANTIGRAVITY_PROMPTS. |
| R-04 | Reporting-regime breaks distort training | High / Med | EDA + explicit training start (OD-06); coverage feature; show L-07. |
| R-05 | Overfitting with ~5 seasons | Med / Med | Simple models; walk-forward; untouched test block; permutation importance on validation. |
| R-06 | Scope creep into ICU/staffing/inventory | High / High | Non-goals list; approval gates; "material scope change needs approval". |
| R-07 | Agent fabricates results or silently changes architecture | Med / High | Phase prompts forbid; verification-before-completion; audit records raw logs. |
| R-08 | CDC dataset renamed/archived/moved | Med / Med | Record SHA-256 + retrieval date; DB is the runtime source; documented in S6. |
| R-09 | Alert misread as a bed-shortage prediction | Med / High | Fixed wording, disclaimer on every screen, L-04. |
| R-10 | Simulated capacity numbers mistaken for real | Med / High | `is_simulated`, badge, placeholder wording, A-08. |
| R-11 | XSS via API text or URL hash | Low / High | `textContent` only, CSP, validated hash params, AT-38. |
| R-12 | Reference-UI brand/art reuse (copyright) | Med / Med | Own brand "CareCast", self-authored icons/illustration; no Apollo assets. |
| R-13 | Dependency vulnerabilities | Med / Med | Minimal deps; `pip-audit`; vendored JS pinned + advisory check (AT-39). |
| R-14 | Time overrun | Med / Med | Should/Could items droppable; gates allow re-scoping with approval. |

---

## 9. User-visible limitations register (shown on S6)

| ID | Limitation |
|---|---|
| L-01 | Data are **U.S.** national surveillance data, not Indian hospitals or any specific hospital. |
| L-02 | Data are **aggregated at jurisdiction level**, not hospital level. |
| L-03 | Scope is **respiratory** admissions (influenza, COVID-19, RSV) only. |
| L-04 | Forecast **admissions** are not **occupancy** or **capacity**; the alert is a planning signal. |
| L-05 | Data are **weekly**; no daily or intraday forecast. |
| L-06 | Reporting hospitals may not represent all hospitals; coverage varies by week. |
| L-07 | Reporting rules changed over time (mandatory → voluntary → CMS-required); RSV was voluntary until 1 Nov 2024. |
| L-08 | Thresholds and capacity inputs are **user assumptions**, not validated rules. |
| L-09 | Capacity illustration is **SIMULATED** and uses a steady-state approximation. |
| L-10 | Models are trained on few seasons; intervals are empirical, not guarantees. |
| L-11 | Forecasts are **not clinically validated**; not for diagnosis or treatment decisions. |
| L-12 | Explanations show model associations, **not causes**. |

---

## 10. Success metrics (measurable, no invented targets)

| Metric | How measured |
|---|---|
| Must-priority acceptance tests executed with recorded result | Count in FINAL_PROJECT_AUDIT (pass **or** documented fail). |
| Model-vs-baseline evidence available for every shown disease | S3 shows MAE/RMSE for all four models per horizon. |
| Reproducibility | AT-43 passes. |
| Security | All applicable PL items reported pass/fail; 0 unresolved critical findings at launch. |
| Demo script completes | 5-step journey J1 (see APP_FLOW §4) executed end-to-end by someone other than the developer. |
| Honesty | 0 hard-coded demo numbers in the UI (AT-31). |

---

## 11. Acceptance test catalog

> Methods: **U** unit · **API** endpoint test · **E2E** browser test · **M** manual review with evidence.

| AT | Feature / NFR | Test (pass condition) | Method | Phase |
|---|---|---|---|---|
| AT-01 | F1 | Running ingest twice yields identical row counts (2nd run inserts 0). | U | P2 |
| AT-02 | F1 | A CSV with a missing/renamed required column aborts with a non-zero exit and clear message. | U | P2 |
| AT-03 | F1 | Fixtures with injected duplicate, gap, negative, non-Saturday date are each detected and logged to T6. | U | P2 |
| AT-04 | F1 | Raw file SHA-256 recorded; unchanged after pipeline run. | U | P2 |
| AT-05 | F1/N1 | Static test: no SQL built via f-string/concatenation/`%`/`.format`. | U | P2→P7 |
| AT-06 | F2 | `GET /observations` returns ascending dates; `from>to` → 422; filters bound the result. | API | P4 |
| AT-07 | F2 | Chart point count = API point count; empty range shows empty state. | E2E | P5 |
| AT-08 | F3 | Perturbing observations after origin *t* leaves the forecast made at *t* unchanged. | U | P3 |
| AT-09 | F3 | `GET /forecast` returns 4 horizons, ascending; `lower ≤ point ≤ upper`; target date = origin + 7·h days. | API | P4 |
| AT-10 | F3/F4 | Empirical coverage on the test block is computed, stored and exposed (no threshold applied). | U/API | P3,P4 |
| AT-11 | F4 | `train_end < valid_start`, `valid_end < test_start` for every run. | U | P3 |
| AT-12 | F4 | Persistence and seasonal-naive predictions match hand-calculated values on a tiny fixture. | U | P3 |
| AT-13 | F4 | MAE/RMSE equal hand/`sklearn` values on the fixture. | U | P3 |
| AT-14 | F4 | Verdict text is "improves" iff test MAE(selected) < MAE(persistence); both branches tested. | U+E2E | P3,P5 |
| AT-15 | F5 | Boundary table: `point==threshold`→Watch (if upper>threshold) ; `point>threshold`→Elevated ; `upper==threshold`→Normal. | U | P4 |
| AT-16 | F5 | Non-numeric, negative, NaN/inf, > bound threshold → 422. | API | P4 |
| AT-17 | F5 | Alert shows tier **text + icon**, threshold value, and the planning-signal disclaimer. | E2E | P5 |
| AT-18 | F6 | Σ contributions + intercept-mean = prediction (|Δ| < 1e-9). | U | P3 |
| AT-19 | F6 | Explanation text is produced from stored numbers; contains no causal terms (list-based test). | U | P4 |
| AT-20 | F6 | Contribution bars sorted by absolute value; labels use text, not colour alone. | E2E | P5 |
| AT-21 | F7 | `adjusted = base × (1 + pct/100)` for point/lower/upper; `pct=0` equals base. | U | P4 |
| AT-22 | F7 | `surge_pct` outside [−50,100] → 422. | API | P4 |
| AT-23 | F7 | UI shows "SCENARIO — not a prediction" and updates on slider change. | E2E | P5 |
| AT-24 | F8 | Worked example (e.g., typical 100/wk, relative_change 1.2, ALOS 5, ratio 6) yields the formula results exactly. | U | P4 |
| AT-25 | F8 | `is_simulated=true` in API; badge visible in UI. | API+E2E | P4,P5 |
| AT-26 | F9 | Each tier returns a fixed, deterministic checklist. | U | P4 |
| AT-27 | F9/F10 | Disclaimer footer present on all six screens. | E2E | P5 |
| AT-28 | F10 | `/meta` returns source, dataset id, retrieved_at, sha256, data_as_of, disclaimers. | API | P4 |
| AT-29 | F10 | S6 lists every L-01…L-12 and all T6 findings. | E2E | P5 |
| AT-30 | F11 | `/summary` returns latest, next-week forecast, tier and watchlist for each *available* disease. | API | P4 |
| AT-31 | F11 | Changing fixture DB values changes UI numbers (no hard-coding). | E2E | P5 |
| AT-32 | F12 | Switching disease updates all S1–S5 widgets; unavailable disease shows reason. | E2E | P5 |
| AT-33 | N1 | CSP, `X-Content-Type-Options`, `Referrer-Policy`, `frame-ancestors`/`X-Frame-Options` present on responses. | API | P4,P7 |
| AT-34 | N1 | Forced server error returns generic JSON; no traceback, path or SQL. | API | P4 |
| AT-35 | N1 | Exceeding the limit returns **429**. | API | P4 |
| AT-36 | N1 | In prod mode: `/docs`, `/redoc`, `/openapi.json` return 404; debug off. | API | P7 |
| AT-37 | N1 | No `Access-Control-Allow-*` and no `Set-Cookie` in any response. | API | P4,P7 |
| AT-38 | N1 | Static grep finds no `innerHTML`/`outerHTML`/`insertAdjacentHTML`/`eval` with API data; payload `<img onerror>` in a mocked field is rendered inert. | E2E+U | P5 |
| AT-39 | N1 | `pip-audit` reports no known critical vulnerabilities; vendored JS version checked against advisories. | M | P7 |
| AT-40 | N3 | Accessibility checklist (UI doc §9) completed with evidence; token contrast ratios verified. | M | P6 |
| AT-41 | N3 | No horizontal body scroll at 375, 768, 1280 px widths. | E2E | P6 |
| AT-42 | UI | VC-01…VC-16 reviewed against reference with screenshots. | M | P6 |
| AT-43 | N2 | Re-running the pipeline on the same raw file reproduces identical metrics. | U/I | P3,P7 |
| AT-44 | All | Full suite passes from a clean clone via `python scripts/verify.py` (command in TRD §12). | I | P7 |
| AT-45 | N6 | Schema test: no column/table names suggesting patient-level fields; DB contains only aggregates. | U | P2,P7 |
| AT-46 | F13 | **Deferred** — not executed in MVP. | — | — |
| AT-47 | Regression | After P5 and P6, backend test suite + API-contract snapshot are **unchanged**, proving frontend work did not alter backend behaviour. | I | P5,P6 |

---

## 12. Traceability matrix

| Feature | Screens | Endpoints | Data / backend components | Phase(s) | Acceptance tests |
|---|---|---|---|---|---|
| **F1** Ingestion & validation | S6 (status) | E1, E2 | T2, T5, T6 · `ingest.py`, `quality.py`, `config/dataset_mapping.toml` | P2 | AT-01…05, AT-45 |
| **F2** Historical explorer | S1, S2 | E4 | T5 | P4, P5 | AT-06, AT-07 |
| **F3** Forecast 1–4 wks | S1, S2 | E5 | T7, T10 · `features.py`, `models.py`, `pipeline.py` | P3, P4, P5 | AT-08, 09, 10, 43 |
| **F4** Baseline vs model | S3, S1 (widget) | E6 | T7, T8, T9 · `evaluate.py` | P3, P4, P5 | AT-11…14 |
| **F5** Early-warning | S1, S2, S5 | E3, E5, E8 | T7 (`default_threshold`) · `planning.py` | P4, P5 | AT-15…17 |
| **F6** Explainability | S4, S1 (widgets) | E7 | T11 · `explain.py` | P3, P4, P5 | AT-18…20 |
| **F7** What-if | S5 | E8 | `planning.py` | P4, P5 | AT-21…23 |
| **F8** Capacity illustration | S5, S1 (tiles) | E2, E8 | `config/planning.toml` · `planning.py` | P4, P5 | AT-24, 25 |
| **F9** Review actions | S1, S2, S5 | E3, E5, E8 | `planning.py` (static table) | P4, P5 | AT-26, 27 |
| **F10** Provenance & limits | S6 + footer on S1–S6 | E2 | T2, T6 | P4, P5 | AT-27…29 |
| **F11** Overview | S1 | E3, E6, E7, E8 | aggregation in `api/routes.py` | P4, P5, P6 | AT-30, 31 |
| **F12** Disease selection | S1–S5 | E2, E3 (+`disease` param) | T4 | P3, P5 | AT-32 |
| **F13** Jurisdiction selector | *(deferred)* | E2 | T3 | — | AT-46 |
| **Cross-cutting** security | all | all | `api/main.py`, `ratelimit.py` | P2–P7 | AT-05, 33…39 |
| **Cross-cutting** UX quality | all | — | `web/` | P5, P6 | AT-40…42, 47 |

---

## 13. Open decisions requiring your approval

| ID | Decision | Default if approved as-is |
|---|---|---|
| OD-01 | Approve MVP scope (§4) and non-goals | Approved |
| OD-02 | Approve stack: FastAPI + SQLite + static web (Streamlit rejected, see TRD §3) | Approved |
| OD-03 | **P2 gate:** confirm dataset, columns and target (count vs rate) from real headers | Decided in P2 |
| OD-04 | Deployment target (local only / Docker / free-tier PaaS) | Local + optional Docker |
| OD-05 | Attempt F13 (state selector) after P6? | No |
| OD-06 | Training-start date after the regime-break review | Decided in P2/P3 |
| OD-07 | Product name "CareCast" and own branding (no "Apollo") | Approved |

---

## 14. Glossary

**NHSN** National Healthcare Safety Network · **HRD** Hospital Respiratory Data · **Persistence baseline** next week = this week · **Seasonal-naive** same week last year · **Walk-forward** refit at each origin using only past data · **Direct strategy** separate model per horizon · **Planning threshold** user-set line against which forecasts are compared · **Little's law** L = λ·W (occupancy ≈ arrival rate × length of stay).
