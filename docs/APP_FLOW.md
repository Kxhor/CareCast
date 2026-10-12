# APP_FLOW — Screens, Navigation, Journeys & States

| Field | Value |
|---|---|
| Document | `docs/APP_FLOW.md` (3 of 8) |
| Version / status | 1.0 — **DRAFT FOR USER APPROVAL** |
| Date | 10 Oct 2026 |
| Depends on | [PRD](PRD.md) (F1–F13, AT-xx) · [UI_UX_DESIGN](UI_UX_DESIGN.md) (components C-xx) · [BACKEND_SCHEMA](BACKEND_SCHEMA.md) (E1–E8) |

---

## 1. Navigation map

```
 CareCast (single-page app, hash routing, same origin)
 │
 ├─ #/overview      S1  Overview            (default route; "/" redirects here)
 ├─ #/forecast      S2  Forecast
 ├─ #/performance   S3  Model performance
 ├─ #/explain       S4  Explainability
 ├─ #/scenario      S5  Scenario planner
 └─ #/data          S6  Data & limitations

 Global shell on every route:  Sidebar · Top bar (disease, data-as-of) · Breadcrumb · Footer disclaimer
 Unknown route → redirect to #/overview + info banner "That page does not exist."
```

| Route | Screen | Sidebar label | Features |
|---|---|---|---|
| `#/overview` | S1 | Overview | F2, F3, F4, F5, F6, F8, F9, F10, F11, F12 |
| `#/forecast` | S2 | Forecast | F2, F3, F5, F9, F12 |
| `#/performance` | S3 | Model performance | F4 |
| `#/explain` | S4 | Explainability | F6 |
| `#/scenario` | S5 | Scenario planner | F5, F7, F8, F9 |
| `#/data` | S6 | Data & limitations | F1 (status), F10 |

The sidebar "Data & disclaimer" box (C-04) always links to `#/data`.

---

## 2. Global behaviour

### 2.1 State and URL parameters

| State | Source of truth | Persistence | Validation |
|---|---|---|---|
| `disease` | Top-bar select | URL: `#/forecast?disease=flu` | Must be in `/meta.diseases[available=true]`; else fall back to `flu` (or first available) + info banner |
| `threshold` override | S2/S5 input | URL param `threshold=` | Finite number ≥ 0 (client check for UX; server is authoritative) |
| `from` / `to` | Top-bar range (S1/S2) | URL params | ISO dates; `from ≤ to`; clamped to data range |
| `horizon` | Tabs (S3/S4) | URL param `h=` | Integer 1–4 |
| Capacity assumptions | S5 form | `localStorage` key `carecast.capacity.v1` inside try/catch | Bounds per BACKEND_SCHEMA §8; corrupt/absent → defaults from `/meta` |
| Scenario `surge_pct` | S5 slider | URL param `surge=` | −50…100 |

URL/hash values are **never** written into the DOM as HTML; they are parsed, validated and rendered via `textContent`.

### 2.2 Route change
1. Validate params → 2. fetch data for the screen (parallel) → 3. render skeletons immediately → 4. fill widgets independently → 5. move focus to the screen `<h1>`, set `document.title` ("Overview · CareCast") and announce via `aria-live`.

### 2.3 First load sequence
`GET /api/v1/meta` → (ok) build top-bar options, banners (stale/quality) → render route. If `/meta` fails with 503 → full-page **Data unavailable** state (§6.1).

### 2.4 Loading strategy
Widgets fail **independently** (F11.2). A failed widget shows its own error block with **Retry**; other widgets stay usable. Requests have a client timeout; a timeout is presented as the generic error state.

---

## 3. User journeys

### J1 — Weekly planning review (primary; **5-step demo script**)

| Step | Persona action | Screen | System response | API |
|---|---|---|---|---|
| 1 | Opens the app | S1 | Hero shows data-as-of, next-week forecast and tier; watchlist shows all diseases | E2, E3 |
| 2 | Reads the forecast and uncertainty | S1 → S2 | Table + chart show 1–4-week point forecast with 80 % interval and threshold | E5, E4 |
| 3 | Notices **Watch/Elevated** for a week | S2 | Alert card + review-action checklist | E5 |
| 4 | Tests "what if admissions rise 20 %?" | S5 | Scenario chart, tier-change table, SIMULATED capacity illustration | E8 |
| 5 | Asks "why this number, and can I trust it?" | S4 → S3 | Contributions/importance + text; baseline comparison verdict | E7, E6 |

### J2 — Check model trustworthiness
S3 → read split timeline → verdict per horizon → metrics table (validation vs test) → backtest chart → coverage statement → S6 for limitations.

### J3 — Stress-test with assumptions
S5 → set surge (slider/preset) → set threshold → edit capacity assumptions (badge: SIMULATED) → results update live (debounced) → "Reset to demo placeholders" returns defaults.

### J4 — Understand data and limits (evaluator Q&A)
S6 → provenance (source, id, retrieved, SHA-256) → quality findings → limitations L-01…L-12 → reproduce commands.

### J5 — First run / no data (developer)
Open app with no DB → full-page **Data unavailable** with the exact command `python -m carecast.pipeline rebuild` → after build, **Retry** → J1.

### J6 — Error recovery
Any widget error → generic message + request-id → **Retry** (single widget) → if repeated 429 → message with wait time from `Retry-After`.

---

## 4. Screen specifications

> Widget IDs are used in tests. Component IDs refer to UI_UX_DESIGN §4.

### S1 — Overview

| Widget | Component | Data (endpoint → field) | Interactions |
|---|---|---|---|
| `w-hero` | C-08, C-09 | E3 → `selected.latest`, `next_week`, `data_as_of` | Chips: "Next-week forecast" (value + interval), "Alert tier" (C-12). Link "Open forecast" → S2 |
| `w-trend` | C-10 | E3 → `selected.recent` (8 wks) | Hover/focus point tooltip; caption "Admissions changed by X % vs prior week" (from `change_pct_vs_prior_week`; `null` ⇒ "n/a") |
| `w-watchlist` | C-11 ×3 | E3 → `watchlist[]` | Click/Enter selects that disease (updates top-bar select + all widgets). Unavailable ⇒ disabled row with reason |
| `w-explain` | C-13 | E7 (h = 1) → `text`, `model_name`; E6/E3 → `beats_persistence` | Link → S4 |
| `w-gauge` | C-14 | E3 → `ring.*` | Static; text alternative "Forecast is N % of the planning threshold (lower N %, upper N %)" |
| `w-forecast-table` | C-15 | E5 → `horizons[]` | Row actions: **Explain** → `#/explain?h=n`, **Scenario** → `#/scenario`, **Details** → `#/forecast` |
| `w-backtest` | C-16 | E6 → `backtest.points` | Horizon fixed = 1; link → S3 |
| `w-drivers` | C-16 (bars) | E7 → `contributions` or `permutation_importance` | Link → S4 |
| `w-capacity` | C-17 ×3 + C-21 | E8 (`surge_pct=0`, stored/default assumptions) → `capacity.horizons[0]` | Badge SIMULATED; link "Edit assumptions" → S5 |

### S2 — Forecast
| Widget | Component | Data | Interactions |
|---|---|---|---|
| `w-controls` | C-05, C-18, C-23 | E2 | Disease select; threshold number input (blur/Enter applies; **Reset to default**); horizon tabs filter the highlighted row |
| `w-forecast-chart` | C-16 | E4 (history) + E5 (forecast) | Series: actual (solid), forecast (dashed), interval band, threshold (dotted + label). Imputed weeks drawn with hollow markers |
| `w-forecast-table` | C-15 | E5 | As S1 |
| `w-alert` | C-12, C-19 | E5 → `tier`, `actions` | Shows tier for the selected horizon; **Review actions** checklist (static text) + footer |

### S3 — Model performance
| Widget | Data | Interactions |
|---|---|---|
| `w-splits` | E6 → `run.train/validation/test` | Timeline bar; dates as text |
| `w-verdicts` | E6 → `verdicts[]`, `selected[]` | One card per horizon: selected model, **"Beats persistence: Yes/No"** (text + icon), test interval coverage as a number |
| `w-metrics` | E6 → `metrics[]` | Split toggle (validation/test); rows = models; columns = horizon × (MAE, RMSE); selected model marked "Selected" (text) |
| `w-backtest-full` | E6 (`horizon=n`) | Horizon tabs; series: actual, selected, persistence |

### S4 — Explainability
| Widget | Data | Interactions |
|---|---|---|
| `w-horizon-tabs` | — | 1–4 weeks |
| `w-contrib` | E7 → `contributions`, `base_value`, `prediction` | Diverging bars sorted by |value|; text labels; if `null` ⇒ notice "Contributions are not available for the selected tree model; showing permutation importance only." |
| `w-importance` | E7 → `permutation_importance` | Bars |
| `w-explain-text` | E7 → `text`, `note` | Always shows "model associations, not causes" |

### S5 — Scenario planner
| Widget | Data | Interactions |
|---|---|---|
| `w-scenario-controls` | E2 defaults | Slider + numeric mirror + presets (0 / 10 / 20 %); threshold input; capacity inputs (4) with inline validation; **Reset to demo placeholders** |
| `w-scenario-chart` | E8 → `horizons[].base/scenario` | Base (dashed teal) vs scenario (dashed amber) + threshold; badge **SCENARIO — not a prediction** |
| `w-tier-changes` | E8 | Table: horizon · base tier · scenario tier · change (text: "unchanged / rises to Watch / rises to Elevated / falls …") |
| `w-capacity-table` | E8 → `capacity.horizons[]` | Rows per horizon: relative change, est. admissions, est. occupied beds, bed gap, nurses per shift; badge **SIMULATED**; "How this is calculated" `<details>` lists `formulae` |
| `w-actions` | E8 → `actions` | Checklist |
Behaviour: input changes are **debounced** (≈ 300 ms) → `POST /scenario`; latest response wins; results region is `aria-live="polite"`.

### S6 — Data & limitations
| Widget | Data | Notes |
|---|---|---|
| `w-provenance` | E2 → `source`, `data_as_of`, `target_kind` | Includes SHA-256 and retrieval date |
| `w-quality` | E2 → `quality_issues[]` | Table; empty ⇒ "No data-quality issues were recorded." |
| `w-regime` | static text (L-07) | Reporting-rule changes |
| `w-limitations` | E2 → `limitations[]` | L-01…L-12 |
| `w-model-summary` | E6 headline | Link → S3 |
| `w-reproduce` | static | Commands from TRD §12 |
| `w-attribution` | static | Data source, Chart.js, icons |

---

## 5. State catalogue (every data widget)

| State | Visual | Text (microcopy) | Behaviour |
|---|---|---|---|
| **Loading** | Skeleton block sized like the widget; `aria-busy="true"` | *(none; skeleton)* | Replaced on response |
| **Success** | Normal | — | Announce route-level changes only (not every widget) |
| **Empty — no points** | Muted icon + message | "No weekly data in this date range. Choose a wider range." | Offer **Reset range** |
| **Empty — series unavailable** | Grey tile | "{Disease} is unavailable: {reason from /meta}." | Link to S6 |
| **Empty — no quality issues / limitations** | Info line | See S6 | — |
| **Error — generic** | Error block (`role="alert"`) | "We couldn't load this section. Please try again." + `Request ID: …` | **Retry** button re-fetches this widget only |
| **Error — validation (422)** | Inline next to the control | "Enter a number between {min} and {max}." | Control keeps focus; no request spam |
| **Error — rate limited (429)** | Banner | "Too many requests. Try again in {n} seconds." | Retry enabled after `Retry-After` |
| **Error — timeout/offline** | Error block | "The server did not respond. Check your connection and retry." | Retry |
| **Stale data** | Warning banner (C-19) | "Data last updated {date}. Newer reports may exist." | Shown if `stale=true` |
| **Quality warning** | Info banner on S1/S2 | "Some weeks were missing or estimated. See Data & limitations." | Shown if `/meta.quality_issues` has `warning`/`error` for the series |
| **Simulated / scenario** | Persistent badge | "SIMULATED — assumption-based" / "SCENARIO — not a prediction" | Cannot be hidden |
| **Model did not beat baseline** | Verdict card (neutral, not alarming) | "On the held-out test weeks, the selected model did **not** improve on the persistence baseline." | Shown honestly everywhere the verdict appears |
| **Tree model selected** | Notice | "Contributions are not available for the selected tree model." | S4 shows permutation importance only |

### 5.1 Full-page states
| State | Trigger | Content |
|---|---|---|
| **Data unavailable** | `/meta` or `/health` returns 503 | Title "Data not loaded"; body: "The forecast database has not been built." + code block `python -m carecast.pipeline rebuild` + **Retry** |
| **No available disease** | All diseases `available=false` | "No series passed validation." + link to S6 quality table |
| **JavaScript disabled** | `<noscript>` | "CareCast needs JavaScript to display charts." + disclaimer text |
| **Unsupported browser** | Missing `fetch`/ES modules | Same as above |

---

## 6. Interaction & keyboard model

| Control | Mouse | Keyboard | Announcement |
|---|---|---|---|
| Sidebar item | Click | Tab / Enter | Route title via live region |
| Hamburger (rail/drawer) | Click | Enter/Space; `Esc` closes drawer; focus trap while open | `aria-expanded` |
| Disease select | Choose | Arrow keys | Widgets re-render; live region "Showing {disease}" |
| Horizon tabs | Click | ←/→ move, Home/End | `role="tab"`, `aria-selected` |
| Slider | Drag | ←/→ (±1), PgUp/PgDn (±10) | Value mirrored in numeric field; results `aria-live` |
| Table row actions | Click | Tab / Enter | Each button has a unique `aria-label` ("Explain 1-week forecast") |
| Charts | Hover tooltip | "View data table" `<details>` is the keyboard path | Table caption states what it shows |

---

## 7. Event → API matrix

| Event | Calls |
|---|---|
| App start | E2 |
| Open S1 | E3, E5, E6 (h = 1), E7 (h = 1), E8 (surge 0) — in parallel |
| Open S2 | E4, E5 |
| Open S3 | E6 (selected h) |
| Open S4 | E7 (selected h) |
| Open S5 | E5 or E3 (base), then E8 on every (debounced) input change |
| Open S6 | E2 (cached) + E6 headline |
| Change disease | Re-run calls of the current screen |
| Change threshold | E5 / E3 / E8 (current screen) |
| Change date range | E4 |
| Retry on a widget | Only that widget's call |

No call writes data. E8 is the only POST and is stateless.

---

## 8. Coverage check (screens ↔ features)

| Feature | Screens that expose it |
|---|---|
| F1 | S6 (status, quality) |
| F2 | S1 (`w-trend`), S2 (`w-forecast-chart`) |
| F3 | S1, S2 |
| F4 | S1 (`w-backtest`, `w-explain` tag), S3 |
| F5 | S1, S2, S5 |
| F6 | S1, S4 |
| F7 | S5 |
| F8 | S1 (`w-capacity`), S5 |
| F9 | S1, S2, S5 |
| F10 | S6 + footer on all |
| F11 | S1 |
| F12 | S1–S5 (top-bar select + watchlist) |
| F13 | *(deferred)* |
