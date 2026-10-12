# UI_UX_DESIGN — Reference Analysis, Design System & Visual Criteria

| Field | Value |
|---|---|
| Document | `docs/UI_UX_DESIGN.md` (4 of 8) |
| Version / status | 1.0 — **DRAFT FOR USER APPROVAL** |
| Date | 10 Oct 2026 |
| Depends on | [PRD](PRD.md) · [APP_FLOW](APP_FLOW.md) · [BACKEND_SCHEMA](BACKEND_SCHEMA.md) |
| Labels | 👁 **OBSERVED** in `Reference_Ui.jpg` · 📐 **MEASURED** (pixel-sampled by me) · 🔎 **INFERRED** (not visible; my judgement) · 🛠 **ADAPTED** (deliberate change for CareCast) |

> **Source image:** `Reference_Ui.jpg`, 736 × 837 px, a down-scaled screenshot of the third-party "Apollo admin 2024" dashboard template. **Real pixel sizes, fonts, and interactions are unknown**; I express layout as **proportions** and set tokens on a standard 4/8-px scale.

---

## 1. Reference UI analysis

### 1.1 Page anatomy 👁

```
┌───────────┬──────────────────────────────────────────────────────────────┐
│ SIDEBAR   │ TOP BAR  [search]                         [icons … avatar]   │
│ (≈17 %    ├──────────────────────────────────────────────────────────────┤
│  of width)│ BREADCRUMB  ⌂ / Medical Dashboard            [date range ▾]  │
│           ├────────────────────────────────────────┬─────────────────────┤
│ logo+burger│ HERO banner (teal) greeting + 2 chips │ "Patients" teal card│  ← row 1  (≈ 75 % / 25 %)
│ avatar    ├──────────────┬──────────────┬──────────┴─────────────────────┤
│ nav list  │ Doctors list │ Reviews      │ Consultation ring + pills      │  ← row 2  (3 equal cards)
│ (17 items)├──────────────┴──────────────┴────────────────────────────────┤
│           │ Patients TABLE (teal header, 9 columns, row action buttons)   │  ← row 3  (full width)
│ [Emergency├──────────────┬──────────────┬────────────────────────────────┤
│  contact] │ Revenue lines│ Pharmacy bars│ Departments (3 stacked tiles)  │  ← row 4  (3 equal cards)
│           ├──────────────┴──────────────┴────────────────────────────────┤
│           │ © Apollo admin 2024                                          │
└───────────┴──────────────────────────────────────────────────────────────┘
```

### 1.2 Region-by-region observations

| Region | 👁 Observed detail |
|---|---|
| **Sidebar** | White, full height, thin right border. Top: teal rounded-square logo tile + bold wordmark + small light-teal rounded hamburger button. Below: circular avatar, name (teal, bold), role (grey). Nav: ~17 rows of outlined teal icon + dark label; **active row** ("Medical Dashboard") = light-teal pill background + filled teal icon tile with white glyph; one row ("Staff") has a right chevron. Bottom: **teal rounded info box** with phone icon, small white label "Emergency Contact" and bold number. |
| **Top bar** | White, thin bottom border. Left: outlined search input with magnifier and "Search" placeholder. Right: flag, star, several outline icons (one with an orange notification dot), user avatar. |
| **Breadcrumb row** | Home icon, "/", current page name in muted text. Right: bordered date-range field with calendar icon (`10/08/2024 - 11/06/2024`). |
| **Page background** | Very light blue-green tint behind all cards. |
| **Hero banner** | Solid teal, rounded. Left: small white "Good Morning," → large bold white name → small white sub-line → two **circular light-green chips** with white outline icons, each with a big bold number and small label ("86 Appointments", "23 Surgeries"). Right: soft light-teal **room illustration** (people, window, shelves, tiled floor). |
| **"Patients" card** | Teal card; white title; **white line chart with green circular markers**, x-axis Sun…Sat in white; caption "Increased patients by [86] in the last Seven days." with the number in a light-green badge. |
| **Doctors card** | White card, bold title. 5 rows: circular photo, bold name, small grey specialty, right-aligned **status pill** (dot + text: green "Available", red "Not Available"). |
| **Reviews card** | Outlined teal tag "Recommend", photo + name, paragraph of review text, filled teal tag "👍 I recommend the doctor.", five gold stars. |
| **Consultation card** | **Dashed teal ring** (≈ 80 % arc) with centred "New: 600 / 80 %" in a pale circle; legend "● New: 600  ● Returning: 360"; two rounded pills with circular teal icon + number + label ("86 Male", "38 Female"). |
| **Patients table** | Full-width card, bold title. **Teal header row, white bold text**: `# · Patient Name · Age · Consulting Doctor · Department · Date · Time · Disease · Actions`. Body: white rows with thin light borders; doctor cell has avatar + name; Actions = **three small square icon buttons** (teal check-circle, red x-circle, teal document); one row shows the red button filled. |
| **Revenue card** | Line chart, **two series** (dark teal and pale teal) with round markers; x Sun…Sat; light vertical dashed gridlines; legend dots "Patients / Income". |
| **Pharmacy card** | Vertical **teal bars**, x Sun…Sat, faint vertical dashed gridlines, no y labels. |
| **Departments card** | Three stacked **pale-tint tiles**: circular pale icon, name, bold teal number ("General Physician 12", "Orthopedic 8", "Cardiologist 6"). |
| **Footer** | Small muted text "© Apollo admin 2024" bottom-left of the content area. |

### 1.3 Colours 📐 (dominant-colour clustering; ±8 per channel due to quantisation + JPEG)

| Where | Measured ≈ | Notes |
|---|---|---|
| Brand teal (hero, trend card, table header, info box) | **#25867F** (cluster #228781–#298F84) | |
| Chart teal (bars / line) | **#429A93** (cluster #409993–#549A92) | |
| Page background | **#E8F3F3** (cluster #E4F4F4–#ECF4F4) | |
| Card / sidebar / top bar | **#FFFFFF** | |
| Sidebar active pill | **#E4F3F3** | |
| Department tile background | **#F2F9F9** | |
| Hero KPI chip | **#7AD672** (cluster #77D871–#7CD474) | Light green |
| Other (status red, gold stars, grey text) | 🔎 inferred: red ≈ #E5484D, gold ≈ #F5B301, text greys | Not reliably samplable |

⚠️ **Accessibility finding.** White text on the **measured** teal #25867F has a contrast ratio of **4.38 : 1**, below the WCAG AA 4.5 : 1 for normal text. 🛠 CareCast therefore uses a slightly darker `--primary-600: #1F7A74` (**5.13 : 1**) for every surface that carries small white text, and keeps the observed teal only for large decorative fills.

### 1.4 Typography 🔎 (image resolution is too low to identify the family)
Sans-serif, rounded/humanist feel; bold headings and bold large numerals; small muted secondary text. 🛠 Use a **system font stack** (no font downloads → simpler CSP, faster, offline).

### 1.5 Spacing & shape 👁 (proportional) → 🛠 tokens
| Observation (proportion) | Adopted token |
|---|---|
| Sidebar ≈ 17 % of screen width | 264 px (rail 72 px when collapsed) |
| Gap between cards ≈ 1.4 % of content width | 16 px (20 px ≥ 1280 px) |
| Card padding ≈ 5 % of card width | 20 px |
| Card corner radius ≈ small-medium | 8 px |
| Table row height ≈ 13 % of a card width | 48 px rows, 44 px header |
| Nav row height | 44 px (touch/keyboard friendly) |

### 1.6 Navigation 👁
Vertical sidebar of ~17 entries (hospital admin, dashboards, appointments, doctors/patients CRUD pages, staff); single active state; collapsible via hamburger 🔎. CareCast needs only **six** destinations (§5).

### 1.7 Interactions & behaviours not visible 🔎
Hover/focus/pressed states, tooltip behaviour, sidebar collapse animation, chart tooltips, date-picker behaviour, responsive behaviour. All are **specified fresh** in this document.

---

## 2. Adaptation map (reference → CareCast)

| Reference element | CareCast element | Reason |
|---|---|---|
| "Apollo" logo/wordmark | **CareCast** wordmark + own icon tile | No third-party branding (R-12, VC-14) |
| Avatar + "Ema Wilson / Department Admin" | **"Demo workspace — Operations planning"** text block (no person, no photo) | No accounts exist (D-04); avoid fake identities |
| 17 nav items | **6** nav items: Overview · Forecast · Model performance · Explainability · Scenario planner · Data & limitations | Scope |
| "Emergency Contact" box | **"Data & disclaimer" box**: "CDC NHSN public data · Not clinically validated" → links to S6 | Keeps the teal info box identity |
| Search field | **Disease selector** (select) | No free-text search exists |
| Flag/star/icon cluster/avatar | **"Data as of {date}"** chip + help link | Only useful items |
| Date range field | **History range** field (F2) | Same pattern, real function |
| Hero "Good Morning, Dr … Your schedule today." | **"Weekly planning brief"** · disease + data-as-of · two chips: **Next-week forecast** and **Alert tier** | Real, data-driven content |
| Hero illustration (people, ward) | **Self-authored simple SVG** (abstract ward/chart motif, same tinted style) | Copyright |
| "Patients" teal card (7-day line) | **"Recent admissions"** (last 8 weeks) + "changed by X % vs prior week" | F2/F11 |
| Doctors list (status pills) | **Disease watchlist** (Normal/Watch/Elevated pills) | F11/F12 |
| Reviews card (tag, text, stars) | **Forecast explanation** (tag "Selected model", text, tag "Beats baseline: Yes/No"); **no stars** | F6/F4; stars would imply invented ratings |
| Consultation ring + Male/Female pills | **Threshold gauge** (forecast ÷ threshold) + **Lower / Upper bound** pills | F5 |
| Patients table | **Forecast table**: # · Target week ending · Horizon · Forecast · Lower · Upper · Threshold · Tier · Actions | F3/F5 |
| Table action buttons (✓ ✗ doc) | **Explain · Scenario · Details** icon buttons (all labelled) | Meaningful actions |
| Revenue (2-series line) | **Backtest: actual vs predicted** (solid vs dashed) | F4 |
| Pharmacy (bars) | **Top drivers** (horizontal bars; text labels) | F6 |
| Departments (3 tiles) | **Capacity illustration tiles** (Est. beds needed · Staffed beds · Nurses per shift) with **SIMULATED** badge | F8 |
| Footer © Apollo | **© CareCast 2026 — student project · public CDC data · not clinically validated** | F10 |

---

## 3. Design tokens (copy-ready `web/assets/css/tokens.css`)

```css
:root {
  /* ── Colour: brand (📐 observed → 🛠 AA-adjusted) ───────────────── */
  --primary-500: #25867F;   /* observed; large decorative fills only (white text 4.38:1 ✗) */
  --primary-600: #1F7A74;   /* DEFAULT brand: white text 5.13:1 ✓, on white 5.13:1 ✓ */
  --primary-700: #1B6F69;   /* text/icons on tinted bg 5.22:1 ✓ */
  --primary-800: #155C57;   /* hover/pressed; white 7.78:1 ✓ */
  --accent-green: #7AD672;  /* hero chips; dark glyph #0F3D2E on it 6.77:1 ✓ */
  --accent-green-ink: #0F3D2E;

  /* ── Colour: surfaces & text ───────────────────────────────────── */
  --bg-page: #E8F3F3;       /* 📐 */
  --bg-surface: #FFFFFF;    /* cards, sidebar, topbar */
  --bg-tint: #F2F9F9;       /* tiles */
  --bg-active: #E4F3F3;     /* active nav pill */
  --text-strong: #1F2D2D;   /* 14.27:1 on white */
  --text-muted: #5B6B6B;    /* 5.58:1 on white · 4.93:1 on page bg */
  --text-on-primary: #FFFFFF;
  --border-subtle: #C9DCDC; /* decorative card/row borders */
  --border-input: #7C9393;  /* 3.25:1 — meets 3:1 for UI components */
  --focus-ring: #0B5FFF;    /* 5.13:1 on white */

  /* ── Colour: status (text + icon + colour, never colour alone) ─── */
  --ok-fg: #146C43;   --ok-bg: #E3F5EA;      /* Normal    5.69:1 */
  --warn-fg: #8A5300; --warn-bg: #FFF1D6;    /* Watch     5.67:1 */
  --bad-fg: #B3261E;  --bad-bg: #FDE7E6;     /* Elevated  5.52:1 */
  --bad-solid: #C62828;                       /* white text 5.62:1 */

  /* ── Colour: data viz ──────────────────────────────────────────── */
  --chart-1: #1F7A74;         /* actual / primary series (solid) */
  --chart-2: #3F9690;         /* comparison series (3.51:1; drawn DASHED + different marker) */
  --chart-forecast: #B45309;  /* forecast line (dashed, 5.02:1) */
  --chart-threshold: #B3261E; /* threshold line (dotted) */
  --chart-band: rgba(31,122,116,.18);   /* prediction interval */
  --chart-grid: #DDE9E9;

  /* ── Typography (🔎 inferred; system stack) ────────────────────── */
  --font-sans: "Segoe UI", system-ui, -apple-system, Roboto, "Helvetica Neue", Arial, sans-serif;
  --fs-xs: .75rem;  --fs-sm: .875rem; --fs-md: 1rem;   --fs-lg: 1.125rem;
  --fs-xl: 1.25rem; --fs-2xl: 1.5rem; --fs-3xl: 2rem;  --fs-display: 2.5rem;
  --fw-regular: 400; --fw-medium: 500; --fw-semibold: 600; --fw-bold: 700;
  --lh-body: 1.5; --lh-tight: 1.2;

  /* ── Space (4-px base), radius, elevation ──────────────────────── */
  --sp-1: 4px; --sp-2: 8px; --sp-3: 12px; --sp-4: 16px; --sp-5: 20px; --sp-6: 24px; --sp-8: 32px; --sp-10: 40px;
  --radius-sm: 6px; --radius-md: 8px; --radius-pill: 999px;
  --shadow-card: 0 1px 2px rgba(16,40,40,.06), 0 2px 8px rgba(16,40,40,.04);

  /* ── Layout ────────────────────────────────────────────────────── */
  --sidebar-w: 264px; --sidebar-rail-w: 72px; --topbar-h: 64px;
  --content-max: 1440px; --gap: 16px; --card-pad: 20px;
  --row-h: 48px; --thead-h: 44px; --target-min: 44px;

  /* ── Motion ────────────────────────────────────────────────────── */
  --t-fast: 150ms; --ease: cubic-bezier(.2,.0,.2,1);
}
@media (min-width: 1280px) { :root { --gap: 20px; } }
@media (prefers-reduced-motion: reduce) { :root { --t-fast: 0ms; } }
```

**Breakpoints:** `sm 576` · `md 768` · `lg 1024` · `xl 1280`. Dark mode is **out of scope** (not in the reference).

### 3.1 Computed contrast ratios (I calculated these)

| Pair | Ratio | WCAG 2.2 AA need | Result |
|---|---|---|---|
| White on observed teal #25867F | 4.38 | 4.5 | ❌ (hence `--primary-600`) |
| White on `--primary-600` #1F7A74 | 5.13 | 4.5 | ✅ |
| `--primary-700` on `--bg-active` | 5.22 | 4.5 | ✅ |
| `--text-strong` on white | 14.27 | 4.5 | ✅ |
| `--text-muted` on white / page bg | 5.58 / 4.93 | 4.5 | ✅ |
| Status fg on status bg (ok/warn/bad) | 5.69 / 5.67 / 5.52 | 4.5 | ✅ |
| `--border-input` on white | 3.25 | 3 (UI) | ✅ |
| `--chart-1` / `--chart-2` / forecast on white | 5.13 / 3.51 / 5.02 | 3 (graphics) | ✅ |
| Reference's pale 2nd series (#9CCFCB) on white | 1.72 | 3 | ❌ (replaced by `--chart-2` + dashes) |

---

## 4. Component catalogue

| ID | Component | Anatomy & behaviour | States |
|---|---|---|---|
| C-01 | **App shell** | Sidebar + top bar + breadcrumb + main (`<main id="main">`) + footer; skip-link to `#main` | default · rail · drawer (mobile) |
| C-02 | **Nav item** | 44 px row; outline icon + label; active = `--bg-active` pill + filled `--primary-600` icon tile; `aria-current="page"` | default · hover · focus · active |
| C-03 | **Brand block** | Own teal tile + "CareCast" + hamburger (button, `aria-expanded`) | default · collapsed |
| C-04 | **Data & disclaimer box** | `--primary-600` rounded box; white text; link to S6 | default · focus |
| C-05 | **Top-bar controls** | Disease `<select>`, data-as-of chip, history-range inputs | default · invalid · disabled |
| C-06 | **Breadcrumb** | `Home / {Screen}` with `<nav aria-label="Breadcrumb">` | — |
| C-07 | **Card** | `--bg-surface`, radius 8, `--shadow-card`, padding 20; `<h2>` title | default · loading · empty · error |
| C-08 | **Hero banner** | `--primary-600` fill, white text, KPI chips left, SVG motif right (decorative, `aria-hidden`) | default · loading skeleton · stale |
| C-09 | **KPI chip** | Circle `--accent-green` + glyph `--accent-green-ink`; big number; label | default |
| C-10 | **Trend card** | `--primary-600` card; white line + `--accent-green` markers; caption with change % badge | default · empty · error |
| C-11 | **Watchlist row** | Icon, disease name, "Latest week: N", tier pill; whole row is a button that selects the disease | default · hover · focus · selected · unavailable |
| C-12 | **Tier badge** | Pill with icon + text: ✔ Normal (ok) · 👁 Watch (warn) · ⚠ Elevated (bad). Unavailable = grey | 4 variants |
| C-13 | **Explanation card** | Outlined tag "Model: …", paragraph, filled tag "Beats baseline: Yes/No", caption "Associations, not causes" | default · tree-model notice |
| C-14 | **Ring gauge** | Inline SVG dashed arc (`stroke-dasharray`), centre text "% of threshold" + label; bound pills "Lower / Upper" | normal · >100 % (full ring + tier colour) · no-threshold |
| C-15 | **Data table** | `<table>` with `<caption>`; teal header, white bold text; 48 px rows; row action icon buttons with `aria-label` | default · sortable? (no) · empty · loading · narrow (h-scroll container) |
| C-16 | **Chart card** | `<figure>` + `<figcaption>` summary + canvas (`role="img"` + `aria-label`) + `<details>` "View data table"; legends use text + line style | loading · empty · error |
| C-17 | **Tile** | `--bg-tint` rounded tile; circular icon; label; bold number; optional **SIMULATED** badge | default · unavailable |
| C-18 | **Form controls** | Select, number input (visible `<label>`, unit suffix, helper/error text), range slider (+ numeric mirror), preset buttons 0/10/20 %, primary & secondary buttons (min 44 px) | default · hover · focus · invalid · disabled |
| C-19 | **Alert banner** | Info / warning (stale data) / error with icon + text; `role="status"` or `role="alert"` | 3 variants |
| C-20 | **Skeleton / empty / error blocks** | Static grey blocks (no shimmer if reduced motion); empty = cause + next step; error = generic message + **Retry** + request-id | — |
| C-21 | **Badges** | `SIMULATED — assumption-based` (amber outline), `SCENARIO — not a prediction` (amber outline), `DEMO DATA PLACEHOLDER` | — |
| C-22 | **Footer disclaimer** | One line: "© CareCast 2026 · Student project · CDC NHSN public data · Not clinically validated · Decision support only" | — |
| C-23 | **Horizon tabs** | `role="tablist"` 1–4 weeks; arrow-key navigation | selected · focus |

**Chart specs (Chart.js, vendored):** line width 2.5 px; actual = solid `--chart-1` with circle markers r = 3; comparison = dashed `--chart-2` with square markers; forecast = dashed `--chart-forecast` with diamond markers; interval = filled band `--chart-band`; threshold = dotted horizontal `--chart-threshold` with direct text label; gridlines `--chart-grid`; axis text `--text-muted` 12 px; tooltips show date + value + series name; number format `Intl.NumberFormat`; dates `10 Oct 2026`. Animations off when `prefers-reduced-motion`.

---

## 5. Screens (layout specs; behaviour in [APP_FLOW](APP_FLOW.md))

### S1 — Overview (`#/overview`) — mirrors the reference row structure
| Row | Columns (12-grid, ≥ 1280 px) | Widgets → endpoints |
|---|---|---|
| 1 | **9** Hero banner · **3** Trend card | C-08 (E3) · C-10 (E3 `recent`) |
| 2 | **4** Disease watchlist · **4** Forecast explanation · **4** Threshold gauge | C-11 (E3) · C-13 (E7 h=1) · C-14 (E3 `ring`) |
| 3 | **12** Forecast table | C-15 (E5) |
| 4 | **4** Backtest chart · **4** Top drivers · **4** Capacity illustration tiles | C-16 (E6) · C-16 (E7) · C-17 (E8 with 0 % surge + stored/default assumptions) |

### S2 — Forecast (`#/forecast`)
Controls row (disease, **threshold input** with "Reset to default", horizon tabs) → large chart (history + forecast line + interval band + threshold line) → forecast table (C-15) → alert card (tier, planning-signal wording) + **review actions** list (F9).

### S3 — Model performance (`#/performance`)
Split timeline bar (train / validation / test with dates) → verdict cards per horizon (selected model; **"Beats persistence baseline: Yes/No"** as text + icon) → metrics table (rows: model; columns: horizon × MAE/RMSE; split toggle validation/test) → backtest chart with horizon tabs → coverage sentence (**value shown, no pass/fail**).

### S4 — Explainability (`#/explain`)
Horizon tabs → **contribution bars** (diverging, sorted by |value|, labels in text) + base value → **permutation importance** bars → plain-language card → notices: "associations, not causes"; "contributions unavailable for tree model" when applicable.

### S5 — Scenario planner (`#/scenario`)
Left column (controls): surge slider (−50…+100) with numeric input + presets 0/10/20, threshold, **capacity assumptions** (4 inputs, SIMULATED badge, "Reset to demo placeholders"). Right column: base-vs-scenario chart (+ threshold) → tier-change table (per horizon) → capacity table/tiles → collapsible "How this is calculated" (formulas) → review actions. Persistent badges: **SCENARIO — not a prediction**, **SIMULATED — assumption-based**.

### S6 — Data & limitations (`#/data`)
Provenance card (source, dataset id, URL, retrieved, SHA-256, data-as-of, target kind) → data-quality findings table → reporting-regime note → limitations list L-01…L-12 → model/evaluation summary → reproduce commands → attributions/licences (data, Chart.js, icons).

**Impeccable/Taste mapping:** S1–S5 = *Operate* mode (dense, scannable, honest numbers); S6 = *Read* mode (comfortable line length ≤ ~75 ch). **Design Read (one line):** *"A calm clinical-teal operations console for planners — dense but legible cards, honest uncertainty, zero decoration beyond the reference's identity."* Suggested dials (use the skills' own scale): **VARIANCE low** (stay faithful to the reference), **MOTION minimal**, **DENSITY medium-high**. Banned: generic purple gradients, mesh backgrounds, fake screenshots, stock people.

---

## 6. Responsive behaviour

| Width | Shell | S1 grid | Tables | Charts |
|---|---|---|---|---|
| ≥ 1280 | Sidebar 264 | 9/3 · 4/4/4 · 12 · 4/4/4 | Full | Height ≥ 280 |
| 1024–1279 | Sidebar → **rail** 72 (icons; accessible names) | 8/4 · 6/6 + 12 · 12 · 6/6 + 12 | Full | ≥ 260 |
| 768–1023 | Rail | 12 · 6/6 · 12 · 12 · 6/6 | Horizontal scroll inside container | ≥ 240 |
| < 768 | **Off-canvas drawer** (hamburger; focus trap while open; `Esc` closes) | Single column | Horizontal scroll inside container (never the body) | ≥ 220 |

Body must never scroll horizontally at **320, 375, 768, 1280** (AT-41). Text must reflow at 200 % zoom.

---

## 7. Content & microcopy rules

| Topic | Rule |
|---|---|
| Alert wording | "Planning signal — not a bed-shortage prediction." Tier text: **Normal / Watch / Elevated** |
| Baseline verdict | Yes → "On the held-out test weeks, the selected model's MAE is lower than the persistence baseline's." No → "On the held-out test weeks, the selected model did **not** improve on the persistence baseline." |
| Explanations | "associated with …", never "caused by …" |
| Simulated | Always badge + label. Never present simulated numbers in the same style as data without the badge |
| Numbers | `Intl.NumberFormat` with thousands separators; tabular numerals; units always shown (admissions per week) |
| Dates | `10 Oct 2026` (unambiguous); API dates are ISO |
| Empty/Error | Say what happened, what the user can do; errors never expose internals |
| Tone | Plain, factual, no hype, no emojis in the product UI |

---

## 8. Asset policy
No Apollo logo/name/artwork/avatars/photos. Icons = own simple outline SVGs (or ISC/MIT icon set with attribution in `web/vendor/LICENSES.md`). Hero motif = self-authored SVG. No external images, fonts or CDNs at runtime (CSP).

---

## 9. Accessibility requirements (WCAG 2.2 AA) — checklist for AT-40

| ID | Requirement | Evidence to record |
|---|---|---|
| A11Y-01 | Token contrast ratios in §3.1 hold in rendered CSS | computed table |
| A11Y-02 | Colour is never the only signal (tier = text + icon; series = line style + marker) | screenshots |
| A11Y-03 | Fully keyboard operable; skip link; logical order; no traps; slider via arrow keys; tabs via arrow keys | manual run notes |
| A11Y-04 | Visible focus indicator ≥ 2 px, ≥ 3:1 against neighbours | screenshot |
| A11Y-05 | Landmarks (`header nav main footer`), single `<h1>` per route, ordered headings | DOM check |
| A11Y-06 | Focus moves to the new `<h1>` and `document.title` updates on route change | E2E assertion |
| A11Y-07 | Tables have `<caption>`, `<th scope>`; controls have programmatic labels | DOM check |
| A11Y-08 | Charts: `figure/figcaption`, text summary, data-table alternative | DOM check |
| A11Y-09 | Dynamic results use `aria-live="polite"`; errors `role="alert"`; loading `aria-busy="true"` | DOM check |
| A11Y-10 | Interactive targets ≥ 24×24 px minimum (target 44 px for primary) | measurement |
| A11Y-11 | Reflow at 320 px and 200 % zoom without 2-D scrolling (except data tables in their own container) | screenshots |
| A11Y-12 | `prefers-reduced-motion` respected; no flashing | manual |
| A11Y-13 | `<html lang="en">`; unique route titles | DOM check |
| A11Y-14 | Form errors identified in text with correction hint | E2E |

Automated aids available without new dependencies: browser Lighthouse (record the findings; do not claim a score is "passing" without stating the audit version) and Playwright's accessibility snapshot.

---

## 10. Visual acceptance criteria (AT-42)

Method: capture S1 at **1280 px width** (and others per §6) via `scripts/capture_screenshots.py`; compare side-by-side with `Reference_Ui.jpg`; initial each line in the audit.

| ID | Criterion |
|---|---|
| VC-01 | Shell regions match the reference: left sidebar, top bar, breadcrumb row with right-aligned range field, content grid, footer line |
| VC-02 | S1 row structure at ≥ 1280 px is **9/3 · 4/4/4 · 12 · 4/4/4** |
| VC-03 | Dominant palette = teal family on a light blue-green page tint with white cards; rendered colours equal §3 tokens |
| VC-04 | Sidebar: brand block, nav with outline icons, **active item = light-teal pill + filled icon tile**, bottom teal info box |
| VC-05 | Hero = solid teal banner, white text hierarchy (small → large → small), two circular light-green KPI chips with large numerals |
| VC-06 | Trend card is teal with a white line and green circular markers |
| VC-07 | Watchlist rows show status pills (dot/icon + text) right-aligned |
| VC-08 | Gauge is a dashed teal arc with centred label and two bound pills beneath |
| VC-09 | Forecast table has teal header with white bold text, bordered rows and three icon action buttons per row |
| VC-10 | Charts use teal series on white cards, week labels on the x-axis, light gridlines |
| VC-11 | Capacity tiles use pale-tint background, circular icon, bold teal number |
| VC-12 | Footer disclaimer visible on every screen |
| VC-13 | Card radius 8 px and padding 20 px (±2 px) everywhere |
| VC-14 | **No Apollo name, logo, avatars, photos or illustration anywhere** |
| VC-15 | Required honesty markers present: tier text+icon, SIMULATED/SCENARIO badges, disclaimers |
| VC-16 | One system font family; tabular numerals in tables/KPIs; scale per §3 |

Deviation from the reference is **allowed only** where §2 lists an adaptation; any other deviation must be recorded in the phase report.
