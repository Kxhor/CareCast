# TRD — Technical Requirements & Design

| Field | Value |
|---|---|
| Document | `docs/TRD.md` (2 of 8) |
| Version / status | 1.0 — **DRAFT FOR USER APPROVAL** |
| Date | 10 Oct 2026 |
| Depends on | [PRD](PRD.md) (features F1–F13, ATs, assumptions A-xx) |
| Evidence labels | ✅ VERIFIED · 📄 REPORTED · 🧪 ASSUMPTION · 💡 RECOMMENDATION · ⚠️ TO-VERIFY (see PRD §0) |

---

## 1. Decision record

| ID | Decision | Justification | Revisit when |
|---|---|---|---|
| **D-01** | MVP = weekly U.S. respiratory-admission forecasting + early-warning + explainability + what-if + simulated capacity illustration | Convergent recommendation of all three reports (PRD §2.3) | Never without user approval |
| **D-02** | **Real CDC/NHSN public data only.** No synthetic operational dataset. Only F8 *assumptions* are simulated, and are labelled | Avoids fabricated-looking results; real data exists and is free (PRD §2.5) | CDC data unusable for all diseases |
| **D-03** | **Python + FastAPI + SQLite (stdlib `sqlite3`) + static HTML/CSS/vanilla-JS frontend + Chart.js (vendored).** No ORM, no Node build, no Streamlit | §3 | A required feature cannot be met |
| **D-04** | **No authentication/authorization.** API is public, read-only on data; the only POST (E8) is a stateless calculation | No accounts, PII or per-user resources exist | **Any** state-changing endpoint, per-user data, upload, or non-public data is added ⇒ authentication becomes REQUIRED and needs user approval |
| **D-05** | Direct multi-horizon forecasting (h = 1…4); candidates = **linear regression on lags** and **HistGradientBoostingRegressor**; references = persistence & seasonal-naive baselines | Simple, explainable, report-aligned (PRD X-07…X-09) | Baselines beat both candidates everywhere (then report honestly; do not add complexity silently) |
| **D-06** | Three-tier alert derived from the forecast interval (PRD F5.2) | Uses uncertainty rather than an arbitrary margin | Evaluator feedback |
| **D-07** | Explainability = additive linear contributions + permutation importance; **SHAP deferred** | No extra dependency; exact additivity for the linear model | Time/need |
| **D-08** | Evaluation = **60/20/20 chronological walk-forward**; MAE, RMSE, interval coverage; **no invented thresholds** | Prevents leakage; keeps test block untouched | Series too short (then adjust fractions with approval) |
| **D-09** | **Offline pipeline writes the DB; the API only reads it.** The API never trains models and **never loads pickled models** | Removes request-time compute and unsafe-deserialisation risk | — |
| **D-10** | Frontend = ES modules, hash router, no CDN at runtime, **strict CSP** | Minimal attack surface; reproducible | Chart.js blocked by CSP (document; do not weaken CSP silently) |

---

## 2. Architecture

```
                          OFFLINE (developer machine, run on demand)
┌────────────────┐   ┌───────────────┐   ┌──────────────┐   ┌───────────────┐   ┌─────────────┐
│ CDC NHSN CSV   │──▶│ ingest.py     │──▶│ features.py  │──▶│ models.py      │──▶│ explain.py  │
│ (data/raw,     │   │ + quality.py  │   │ (lags, season│   │ + evaluate.py  │   │ (contrib.,  │
│  untouched,    │   │ validate/map  │   │  coverage)   │   │ walk-forward   │   │  permutation)│
│  SHA-256 kept) │   └──────┬────────┘   └──────────────┘   └───────┬────────┘   └──────┬──────┘
└────────────────┘          │ writes (rw)                            │ writes (rw)       │
                            ▼                                        ▼                   ▼
                      ┌─────────────────────────  SQLite: data/carecast.db  ──────────────────┐
                      │ T2 sources · T3/T4 dims · T5 observations · T6 quality · T7–T11 models │
                      └───────────────────────────────┬────────────────────────────────────────┘
                                                      │ read-only connection (mode=ro, query_only)
                          ONLINE (uvicorn, single process)
                                                      ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│ FastAPI app  carecast.api.main                                                            │
│  middleware: request-id · security headers · body-size cap · rate limit · generic errors  │
│  routes (E1–E8) → planning.py (tiers, scenario, capacity illustration) → SQL (parameterised)│
│  static mount "/" → web/  (same origin ⇒ no CORS)                                          │
└───────────────────────────────────────────────┬───────────────────────────────────────────┘
                                                │ JSON over HTTP(S)
                                                ▼
                    Browser: web/index.html + ES modules + Chart.js (vendored) — S1…S6
```

**Trust boundaries:** (1) CDC CSV → ingest (validated, never executed); (2) browser → API (all input untrusted); (3) API → DB (read-only, parameterised); (4) API → browser (rendered with `textContent` only).

---

## 3. Stack choice, cost and limitations (Ponytail ladder applied)

> Ladder: need it? → already in repo? → stdlib? → platform? → installed package? → one line? → minimum code.

| Layer | Choice | Why | Cost | Limitations / trade-offs | Rejected |
|---|---|---|---|---|---|
| Language | Python ≥ 3.11 | Required skills (pandas, scikit-learn); `tomllib` in stdlib | Free | — | R, Julia |
| Data | pandas, numpy | Standard; needed for time-series features | Free | Memory fine at this scale | polars (new dep) |
| ML | scikit-learn (`LinearRegression`, `HistGradientBoostingRegressor`, `permutation_importance`) | Covers models, metrics, explainability with **one** dependency | Free | No native prediction intervals → empirical residual quantiles | statsmodels/SARIMA, XGBoost, SHAP, PyTorch (extra deps, no demonstrated need) |
| API | FastAPI + uvicorn (Pydantic included) | Typed validation = backend input validation (INC-03); small | Free | Adds an API layer vs. a one-file dashboard | Flask (manual validation), Django (heavy) |
| Storage | SQLite via `sqlite3` | Zero-ops, single file, read-only mode, FK/CHECK constraints | Free | Single-writer; fine because only the offline pipeline writes | PostgreSQL (server), CSV-only (no constraints/indexes), SQLAlchemy (unneeded) |
| Frontend | Static HTML/CSS + vanilla JS ES modules | No build step; faithful reproduction of the reference layout; CSP-friendly | Free | Hand-written components; no framework conveniences | React/Vite (Node toolchain + deps), **Streamlit** |
| Charts | Chart.js (UMD, **vendored**, pinned) | Lightweight; line/bar needed; no CDN | Free (MIT) | Ring gauge drawn with inline SVG instead | Plotly.js (≈ MB-scale bundle), D3 (more code) |
| Tests | pytest, httpx (TestClient), Playwright (dev only) | Unit/API/E2E + screenshots with **one** browser tool | Free | Playwright downloads a browser (dev only) | Cypress/Selenium |
| Audit | pip-audit, bandit (optional, dev only) | Dependency and static security checks | Free | Needs network when run | — |

### 3.1 Why not Streamlit (Reports A & C recommended it)

| Concern | Detail |
|---|---|
| Visual fidelity | The reference needs a fixed sidebar, hero banner, card grid, teal table header, dashed ring. Reproducing that in Streamlit means overriding its generated DOM with brittle CSS. |
| Brief requirements | The brief asks for backend schema, API endpoints, a frontend↔backend regression check and endpoint-level security review (headers, CORS, rate limits). Those map naturally to an API/web split. |
| Honest cost | More hand-written code (~static JS). Mitigated: no framework, no build. |
| Fallback | If P5 fails its gate, a Streamlit UI over the same `planning.py`/DB is the documented fallback (needs user approval). |

### 3.2 Dependency policy
- **Runtime:** `fastapi`, `uvicorn`, `pandas`, `numpy`, `scikit-learn`. *(Pydantic/Starlette arrive transitively.)*
- **Dev-only:** `pytest`, `httpx`, `playwright`, `pip-audit`, `bandit` (optional).
- **Vendored JS:** `web/vendor/chart.umd.min.js` (exact version, SHA-256 and licence recorded in `web/vendor/VERSIONS.md`).
- **Pinning:** after install, freeze **exact** versions into `requirements.txt` / `requirements-dev.txt`. Do not guess version numbers in docs.
- **Adding any other dependency requires user approval** (record rationale in the phase report).

---

## 4. Modules and responsibilities

| Module | Responsibility | Writes DB? |
|---|---|---|
| `carecast/settings.py` | Read env vars + TOML config; fail fast on invalid values | No |
| `carecast/db.py` | `connect_rw()`, `connect_ro()` (URI `mode=ro`, `PRAGMA query_only=ON`, `foreign_keys=ON`), migration runner | — |
| `carecast/ingest.py` | Map columns, parse/validate CSV, upsert T2/T3/T4/T5 | Yes (offline) |
| `carecast/quality.py` | Data-quality checks → T6 | Yes (offline) |
| `carecast/features.py` | Build lag/seasonal/coverage features at origin *t* for horizon *h* (leak-free) | No |
| `carecast/models.py` | Baselines + candidate models; fit/predict | No |
| `carecast/evaluate.py` | Split, walk-forward, metrics, residual quantiles, coverage | Yes (offline) |
| `carecast/explain.py` | Contributions, permutation importance, templated text | Yes (offline) |
| `carecast/planning.py` | Tier rule, scenario math, capacity illustration, action table | No (pure functions) |
| `carecast/pipeline.py` | CLI: `migrate · ingest · train · rebuild · check` | Yes (offline) |
| `carecast/api/main.py` | App factory, middleware, handlers, static mount | No |
| `carecast/api/routes.py` | E1–E8 | No (reads) |
| `carecast/api/schemas.py` | Pydantic request/response models | — |
| `carecast/api/ratelimit.py` | In-memory sliding-window limiter | — |

`planning.py` contains **pure functions** (no I/O) so tier, scenario and capacity logic are unit-testable (AT-15, 21, 24, 26).

---

## 5. Data & ML pipeline

### 5.1 Stages

| # | Stage | Detail | Output |
|---|---|---|---|
| 1 | Acquire | Developer downloads CSV(s) manually (no end-user upload). Raw files stay in `data/raw/`, untouched. | SHA-256, row count |
| 2 | Map & validate | `config/dataset_mapping.toml` maps *logical* fields → CSV columns. Missing required column ⇒ abort. | T2, T3, T4 |
| 3 | Clean | Parse Saturday week-ending; numeric coercion with error log; de-duplicate by key; reindex to a complete weekly calendar; flag imputed weeks (gap ≤ 2). | T5, T6 |
| 4 | EDA gate (P2) | Plot/inspect per disease: seasonality, regime breaks, zeros, coverage. User decides training start (OD-06) and which diseases qualify (R-02). | Decision log |
| 5 | Features | See §5.2. | In-memory frames |
| 6 | Split | 60/20/20 on **target weeks**, chronological (A-04). | T7 (dates, n) |
| 7 | Walk-forward | For each origin *t* in a block and each *h*: fit using only rows whose **target week ≤ t** (known at *t*), predict *y*ₜ₊ₕ. Refit stride from config. | T9 predictions |
| 8 | Metrics | MAE, RMSE per model × horizon × split; relative MAE vs persistence. | T8 |
| 9 | Select | Per horizon, choose the candidate with lowest **validation** MAE. | T8 `is_selected` |
| 10 | Intervals | q10/q90 of signed validation residuals of the selected model (per horizon); `lower = point + q10` (clipped ≥ 0), `upper = point + q90`. Coverage measured on **test**. | T8, T10 |
| 11 | Final forecast | Refit selected model on all data through the last observed week; predict h = 1…4. | T10 |
| 12 | Explain | §5.4. | T11 |
| 13 | Persist | Single transaction; set previous run `is_current=0`, new run `is_current=1`. | T7 |

### 5.2 Features at origin *t*, horizon *h* (🧪 configurable)

| Feature | Definition | Note |
|---|---|---|
| `y_lag0 … y_lag3` | *y*ₜ, *y*ₜ₋₁, *y*ₜ₋₂, *y*ₜ₋₃ | Report A: lags 1, 2, 4 → `roll_mean_4` covers the longer window |
| `roll_mean_4` | mean(*y*ₜ₋₃…*y*ₜ) | Smooths reporting noise |
| `seasonal_lag52` | *y* at target week − 52 weeks | Only if ≥ 52 weeks precede; else feature omitted (config) |
| `woy_sin`, `woy_cos` | Sine/cosine of the **target** week-of-year | Smooth seasonality, no one-hot |
| `pct_reporting` | Reporting coverage at *t* (if the column exists) | ⚠️ TO-VERIFY column |

**Leakage rule:** features use data ≤ *t*; training rows for a refit at *t* are origins *s* with *s + h ≤ t*. AT-08 enforces this by perturbing post-*t* values.

### 5.3 Models

| Name | Type | Role |
|---|---|---|
| `baseline_persistence` | ŷₜ₊ₕ = *y*ₜ | Primary reference for "beats baseline" |
| `baseline_seasonal_naive` | ŷₜ₊ₕ = *y*ₜ₊ₕ₋₅₂ | Additional reference (when available) |
| `linear_lag` | `LinearRegression` on §5.2 features | Candidate (explainable) |
| `hgb_lag` | `HistGradientBoostingRegressor` (fixed `random_state`) | Candidate (non-linear comparator) |

Negative predictions are clipped to 0 (counts cannot be negative) and the clipping is noted in the run config.

### 5.4 Explainability

| Method | Applies to | Definition | Persisted as |
|---|---|---|---|
| Additive contribution | `linear_lag` | `contribution_j = coef_j × (x_j − mean_train_j)`; `base = mean training prediction`; **`base + Σ contribution_j = prediction`** | T11 `method='linear_contribution'` (+ `__base__` row) |
| Permutation importance | any selected model | `sklearn.inspection.permutation_importance` on the validation block, scoring = negative MAE, `n_repeats` from config, fixed seed | T11 `method='permutation_importance'` |

If `hgb_lag` is selected for a horizon, only permutation importance exists; the UI says so (no pretending that a linear explanation describes a tree model).

**Plain-language text** is built from templates with stored numbers (e.g., "The largest positive contribution to the 1-week forecast is associated with *recent admissions (last week)*."). It never states causation (AT-19).

### 5.5 Reproducibility
Fixed `random_seed`; library versions, config hash, raw-file SHA-256 and `code_version` (git commit if available) stored in `model_runs.config_json` (T7). Re-running on the same inputs reproduces metrics exactly (AT-43).

### 5.6 What the pipeline must **not** do
Random shuffling · fitting on test data · selecting on test metrics · inventing thresholds · hiding a failed baseline comparison · silently dropping series · writing results by hand.

---

## 6. API summary (full contract in [BACKEND_SCHEMA](BACKEND_SCHEMA.md))

| ID | Method & path | Purpose | Features |
|---|---|---|---|
| E1 | `GET /api/v1/health` | Liveness + DB readable + data-as-of | F1, F10 |
| E2 | `GET /api/v1/meta` | Diseases, jurisdictions, horizons, provenance, disclaimers, defaults | F8, F10, F12 |
| E3 | `GET /api/v1/summary` | Overview widgets for the selected disease + watchlist | F5, F9, F11 |
| E4 | `GET /api/v1/observations` | Historical series | F2 |
| E5 | `GET /api/v1/forecast` | 1–4-week forecast + tier per week | F3, F5, F9 |
| E6 | `GET /api/v1/evaluation` | Metrics + backtest series | F4 |
| E7 | `GET /api/v1/explain` | Contributions, importances, text | F6 |
| E8 | `POST /api/v1/scenario` | Stateless what-if + capacity illustration | F5, F7, F8, F9 |

---

## 7. Frontend architecture (full spec in [UI_UX_DESIGN](UI_UX_DESIGN.md) and [APP_FLOW](APP_FLOW.md))

| Concern | Decision |
|---|---|
| Routing | Hash router: `#/overview`, `#/forecast`, `#/performance`, `#/explain`, `#/scenario`, `#/data` |
| State | `store.js` (selected disease, date range, threshold override). Capacity assumptions kept in `localStorage` inside try/catch (per-viewer convenience; not sensitive). URL hash params are **validated** before use. |
| Rendering | Build DOM with `createElement` + `textContent`. **No `innerHTML`/`outerHTML`/`insertAdjacentHTML`/`eval`/`new Function`** with dynamic data (AT-38). |
| Data access | `api.js` single `fetch` wrapper: timeout, JSON parse guard, generic error mapping, `request_id` surfaced. |
| Charts | `charts.js` wraps Chart.js; each chart has a text summary + "view data table" fallback. Ring gauge is inline SVG. |
| Icons | Own SVG sprite `web/assets/icons.svg` (simple outline icons; or copied from an ISC/MIT icon set with attribution in `web/vendor/LICENSES.md`). |
| Styles | `tokens.css` → `base.css` → `layout.css` → `components.css`. **No inline `style=""` attributes** (CSP). |

---

## 8. Configuration & environments

| Variable | Default | Meaning |
|---|---|---|
| `CARECAST_ENV` | `prod` | `dev` enables reload helpers and optional docs; `prod` disables them |
| `CARECAST_DB_PATH` | `data/carecast.db` | SQLite path (must be **outside** `web/`) |
| `CARECAST_ENABLE_DOCS` | `0` | `/docs`, `/redoc`, `/openapi.json`; honoured **only** when `CARECAST_ENV=dev` |
| `CARECAST_RATE_GET_PER_MIN` | `60` | 🧪 A-10 |
| `CARECAST_RATE_POST_PER_MIN` | `20` | 🧪 A-10 |
| `CARECAST_TRUSTED_PROXY` | `0` | `1` ⇒ trust `X-Forwarded-For` (only behind a known proxy) |
| `CARECAST_HSTS` | `0` | `1` ⇒ send HSTS (only when served over HTTPS) |
| `CARECAST_LOG_LEVEL` | `INFO` | stdlib logging |

**No secrets exist in this design.** `.env.example` lists the variables above; `.env` is git-ignored; values are read from the process environment (no `python-dotenv`).

TOML configs: `config/pipeline.toml` (split, horizons, features, models, interval level, threshold percentile, seeds, training start), `config/dataset_mapping.toml` (logical → CSV columns, jurisdiction/disease code maps), `config/planning.toml` (capacity placeholders, bounds, action checklists, limitations and disclaimer text).

---

## 9. Security architecture

### 9.1 Threat model (STRIDE-lite)

| Asset | Threat | Control |
|---|---|---|
| Integrity of displayed forecasts | Tampered CSV / DB | Raw SHA-256 recorded; DB opened read-only by API; DB outside web root |
| API availability | Request floods / large bodies | In-memory rate limit; body-size cap; no heavy compute in request path |
| Browser users | Stored/reflected XSS | `textContent` only; CSP `script-src 'self'`; validated hash params; no user-generated content stored |
| DB | SQL injection | Parameterised queries only; read-only connection; AT-05 static test |
| Server internals | Info disclosure | Generic errors; no stack traces; docs disabled in prod; no paths in responses |
| Supply chain | Vulnerable/malicious dependency | Few deps; pinned; `pip-audit`; vendored JS pinned with SHA-256 |
| Clickjacking | Framing | `frame-ancestors 'none'` + `X-Frame-Options: DENY` |
| Path traversal | Static handler | Starlette `StaticFiles`; `web/` contains only public assets |
| Privacy | PII leakage | None collected; AT-45 |

### 9.2 Security headers (all responses)

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
X-Content-Type-Options: nosniff
Referrer-Policy: no-referrer
X-Frame-Options: DENY
Permissions-Policy: geolocation=(), camera=(), microphone=()
Cache-Control: no-store            (API responses)
Strict-Transport-Security: …       (only when CARECAST_HSTS=1)
```
Chart.js sets styles through the CSSOM (allowed under `style-src 'self'`). If the CSP blocks it in P5, **document and ask** — do not add `'unsafe-inline'` silently.

### 9.3 Control applicability matrix (user's two master prompts → CareCast)

> Rule from the brief: mark irrelevant controls **NOT APPLICABLE** with reasons; add no infrastructure just to tick a box.

**Incremental review items (INC-01…10) — Master Prompt #1**

| ID | Item | CareCast status | Concrete check / reason |
|---|---|---|---|
| INC-01 | Authentication & authorization on every endpoint | **NOT APPLICABLE** (D-04) | Public aggregate data; no accounts/resources. **Verify:** no endpoint writes data; E8 is stateless. If that ever changes ⇒ becomes REQUIRED. |
| INC-02 | No hard-coded secrets/keys/tokens | APPLICABLE | Secret scan of repo + history; `.env` ignored; none expected. |
| INC-03 | Backend input validation | APPLICABLE | Pydantic enums/bounds on every parameter; unknown fields rejected; AT-06/16/22. |
| INC-04 | Safe error messages | APPLICABLE | Custom handlers; AT-34. |
| INC-05 | Sanitise user-generated content | APPLICABLE (light) | No UGC stored. Only numbers/enums typed by user; render via `textContent`; AT-38. |
| INC-06 | Parameterised queries | APPLICABLE | AT-05. |
| INC-07 | File uploads validated/stored securely | **NOT APPLICABLE** | No upload endpoint (CSV is loaded by the developer via CLI). **Verify:** no multipart route; `python-multipart` not installed. |
| INC-08 | Rate limiting on abusable endpoints | APPLICABLE | Limiter on `/api/*`, stricter on E8; AT-35. |
| INC-09 | CSRF on state-changing operations | **NOT APPLICABLE** | No cookies/sessions; no state-changing authenticated action; E8 only computes. **Verify:** no `Set-Cookie` (AT-37). |
| INC-10 | Sensitive data encrypted / not over-exposed | APPLICABLE (light) | No sensitive data. Ensure responses omit internal paths/ids beyond need; TLS in transit at deployment; at-rest encryption N/A for public aggregate data. |

**Pre-launch items (PL-01…13) — Master Prompt #2**

| ID | Item | CareCast status | Concrete check / reason |
|---|---|---|---|
| PL-01 | Secrets in env vars, not code | APPLICABLE | No secrets; config only via env/TOML; scan. |
| PL-02 | Backend input validation | APPLICABLE | As INC-03. |
| PL-03 | Parameterised queries | APPLICABLE | As INC-06. |
| PL-04 | Authn/authz on all endpoints | **NOT APPLICABLE** (D-04) | As INC-01; re-verified at launch. |
| PL-05 | Errors expose no internals | APPLICABLE | As INC-04. |
| PL-06 | CORS locked to own domain | APPLICABLE | Same-origin serving ⇒ **no CORS middleware**; verify no `Access-Control-*`. If UI is ever hosted elsewhere ⇒ allow exactly that one origin. |
| PL-07 | Debug off | APPLICABLE | `CARECAST_ENV=prod`; no reload; docs/openapi 404; AT-36. |
| PL-08 | Cookies secure/httpOnly/sameSite | **NOT APPLICABLE** | The app sets no cookies. Verify absence. |
| PL-09 | HTTPS enforced | APPLICABLE **at deployment** | Platform TLS + redirect + `CARECAST_HSTS=1`. Local HTTP demo is N/A (state it). |
| PL-10 | Rate limiting on login & sensitive endpoints | APPLICABLE (partial) | No login ⇒ login part N/A; limiter on `/api/*` and E8. |
| PL-11 | File uploads | **NOT APPLICABLE** | As INC-07. |
| PL-12 | Dependencies free of known critical vulnerabilities | APPLICABLE | `pip-audit`; JS advisory check; AT-39. |
| PL-13 | No test creds/dummy data/dev artifacts | APPLICABLE | Fixtures excluded from prod image; DB holds only real CDC data; placeholders labelled; `.gitignore` audit. |

---

## 10. Deployment (Phase 7; decision OD-04)

| Option | Cost | Notes |
|---|---|---|
| **Local demo (default)** | Free | `uvicorn` on `127.0.0.1`; HTTPS controls marked N/A for local. |
| Docker image | Free | Slim Python base, **non-root user**, copy `carecast/`, `web/`, `config/`, prebuilt `data/carecast.db`; `HEALTHCHECK` → `/api/v1/health`; no dev deps; no fixtures. |
| Free-tier PaaS | Free tier ⚠️ TO-VERIFY (terms change) | Platform provides TLS. Set `CARECAST_ENV=prod`, `CARECAST_HSTS=1`, `CARECAST_TRUSTED_PROXY=1` **only if** the platform's proxy is trusted. DB baked into the image (read-only; ephemeral FS is fine). |

Data refresh = re-run the pipeline locally, rebuild the image. No runtime writes.

---

## 11. Observability & operations
- stdlib `logging` to stderr; one line per request: `request_id, method, path, status, duration_ms`. No bodies, no stack traces to clients.
- `GET /api/v1/health` (E1) reports `db_ok` and `data_as_of`.
- Stale-data banner in UI when `data_as_of` is older than 2 reporting weeks (A-11).

---

## 12. Verification commands (canonical)

```bash
# setup
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# data + model (offline)
python -m carecast.pipeline rebuild               # migrate → ingest → train
python -m carecast.pipeline check                 # data-quality report

# run
CARECAST_ENV=dev python -m uvicorn carecast.api.main:app --host 127.0.0.1 --port 8000

# tests
python -m pytest -q                               # unit + API
python -m pytest tests/e2e -q                     # Playwright E2E (dev)
python scripts/verify.py                          # AT-44: full suite + pip-audit + SQL-guard + contract snapshot
python scripts/capture_screenshots.py             # real screenshots → reports/screenshots/
```
`scripts/verify.py` must exit non-zero on any failure and print a summary that is copied **verbatim** into the audit.

---

## 13. Repository layout (target)

```
carecast/
├─ docs/                       # the 8 documents (+ nothing else)
├─ config/                     # pipeline.toml · dataset_mapping.toml · planning.toml
├─ data/
│  ├─ raw/                     # CDC CSVs (git-ignored if large) — never edited
│  ├─ carecast.db              # built artifact (git-ignored)
│  └─ README.md                # provenance, URLs, retrieval dates, SHA-256, decisions
├─ migrations/                 # 0001_core_data.sql · 0002_forecasting.sql  (forward-only)
├─ carecast/
│  ├─ __init__.py  settings.py  db.py
│  ├─ ingest.py  quality.py  features.py  models.py  evaluate.py  explain.py  planning.py  pipeline.py
│  └─ api/  main.py  routes.py  schemas.py  ratelimit.py
├─ web/
│  ├─ index.html
│  ├─ assets/css/  tokens.css  base.css  layout.css  components.css
│  ├─ assets/js/   app.js  router.js  store.js  api.js  charts.js  format.js
│  │              components/*.js   views/overview.js forecast.js performance.js explain.js scenario.js data.js
│  ├─ assets/icons.svg
│  └─ vendor/      chart.umd.min.js  VERSIONS.md  LICENSES.md
├─ tests/
│  ├─ fixtures/                # tiny synthetic CSV/DB, labelled TEST-ONLY
│  ├─ unit/  api/  e2e/  contract/openapi.snapshot.json
├─ scripts/                    # verify.py · capture_screenshots.py
├─ reports/                    # phase reports · security/SR-n.md · logs/ · screenshots/
├─ requirements.txt  requirements-dev.txt  pyproject.toml (optional)
├─ .env.example  .gitignore  .dockerignore  Dockerfile (P7)  README.md
```
`reports/` is where the agent writes **raw evidence**; [FINAL_PROJECT_AUDIT](FINAL_PROJECT_AUDIT.md) is compiled from it.

---

## 14. Known technical limitations & future work
Single-process in-memory rate limiter (resets on restart; per-process) · no model registry · intervals are empirical and series-specific · ICU/occupancy columns in DS-2 ⚠️ unexplored · state-level (F13) · SHAP · SARIMA/XGBoost · automated data refresh · role-based access if hospital data is ever added.
