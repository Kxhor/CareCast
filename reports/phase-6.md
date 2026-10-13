# Phase 6 Completion Report — UI Polish, Accessibility & Responsive Fidelity

**Project:** CareCast — Explainable Respiratory Admission Forecasting & Capacity Early-Warning System  
**Audit Standard:** Strict Rule G-0 & WCAG 2.1 AA Compliance  
**Date:** 2026-10-14  
**Status:** **READY FOR REVIEW — AWAITING "APPROVED: PHASE 6"**

---

## 1. Executive Summary & Verification Evidence

In Phase 6, CareCast's frontend was elevated to professional clinical grade with strict adherence to `UI_UX_DESIGN.md`, `APP_FLOW.md`, `TRD.md` §7/§9.2, and `Reference_Ui.jpg`.

### Key Verification Metrics
- **Backend Suite (Regression R2):** **99 passed, 0 failures** in 10.46s (identical to Phase 4 baseline).
- **OpenAPI Contract Snapshot SHA-256:** `F083424340A1973CCDF07E975729156564207FF44109B8A4459F011A677B4259` (identical to baseline).
- **Frontend E2E Test Suite:** **58 passed, 0 failures** in 63.74s across Chromium/Edge:
  - `tests/e2e/test_phase6_polish.py`: 46 passed (AT-40 a11y, AT-41 responsive, AT-42 visual criteria).
  - `tests/e2e/test_ui_flows.py`: 12 passed (AT-07, AT-14, AT-17, AT-20, AT-23, AT-25, AT-27, AT-29, AT-31, AT-32, AT-38).
- **Lighthouse Accessibility Score:** **100 / 100** (Lighthouse v13.5.0; 0 failing audits).
- **DOM Security Sinks:** **0** occurrences of `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `eval`, or dynamic constructors.
- **Inline Style Violations:** **0** inline `style="..."` attributes across all HTML/JS components.
- **Backend Code Invariance:** Exactly **0** backend Python files (`carecast/`) modified in Phase 6.

---

## 2. Side-by-Side Comparison: S1 at 1280 px vs Reference_Ui.jpg

CareCast was aligned directly with the layout and structure of `Reference_Ui.jpg` while respecting the clinical adaptations codified in `UI_UX_DESIGN.md` §2.

| Reference Element (`Reference_Ui.jpg`) | CareCast Cockpit (S1 at 1280 px) | Status & Alignment Notes |
|---|---|---|
| **Grid Proportions** | 4-row layout: Row 1 (9/3), Row 2 (4/4/4), Row 3 (12), Row 4 (4/4/4) | **Matches approved design spec with documented adaptations** (VC-02). Measured CSS grid columns verify 9/3, 4/4/4, 12, 4/4/4 spans. |
| **Top Shell & Breadcrumb** | Top bar with search capsule + right utilities; breadcrumb with date range field | **Matches approved design spec with documented adaptations** (VC-01). Adapted search input into disease selector capsule; date range reflects historical training surveillance window. |
| **Sidebar Navigation** | Left rail with brand tile, profile block, vertical navigation, active item highlight, and bottom emergency box | **Matches approved design spec with documented adaptations** (VC-04). Active item renders with light-teal background pill and teal filled icon; emergency box adapted into CDC disclaimer card linked to S6. |
| **Hero Banner** | Teal banner, greeting/title hierarchy, two circular KPI chips, right ward illustration | **Matches approved design spec with documented adaptations** (VC-05). Features next-week forecast chip + operational tier chip; right illustration is self-authored SVG ward motif. |
| **Trend Sparkline Card** | Solid teal card with white curve line chart and green circular markers | **Matches approved design spec with documented adaptations** (VC-06). Renders recent 8-week admissions sparkline with percentage change badge. |
| **Watchlist / Doctors Card** | 3–4 stacked rows with circular icons, bold label, and right-aligned status pill | **Matches approved design spec with documented adaptations** (VC-07). Status pills display operational tier (`Normal`, `Watch`, `Elevated`) with text + dot icon. |
| **Gauge / Consultation Card** | Dashed teal arc gauge with centred percentage and two bound pills beneath | **Matches approved design spec with documented adaptations** (VC-08). Renders capacity gauge (forecast ÷ threshold) with Lower and Upper interval pills. |
| **Explanation / Reviews Card** | Tag pill, plain text explanation, model verdict tag | **Matches approved design spec with documented adaptations** (VC-07 / VC-15). Replaced doctor reviews with selected model tag, non-causal attribution text, and persistence baseline verdict badge. |
| **Forecast / Patients Table** | Full-width table with teal header, bold white text, zebra hover rows, and 3 icon action buttons | **Matches approved design spec with documented adaptations** (VC-09). Columns: `#`, `Target Week Ending`, `Horizon`, `Forecast`, `Lower`, `Upper`, `Threshold`, `Tier`, `Actions` (Explain, Scenario, Details). |
| **Row 4 Analytics Cards** | 3 equal-width cards (Backtest line, Drivers bar chart, Capacity tiles) | **Matches approved design spec with documented adaptations** (VC-10 / VC-11). Features actual vs predicted backtest curves, top feature importance bars, and 3 stacked simulated capacity tiles. |
| **Footer** | Muted text at bottom-left/center | **Matches approved design spec with documented adaptations** (VC-12). Mandatory student disclaimer rendered across every view. |

---

## 3. Accessibility Checklist (A11Y-01 to A11Y-14)

All requirements under WCAG 2.1 AA and `UI_UX_DESIGN.md` §9 have been validated with empirical evidence.

### A. Computed Contrast Table (A11Y-01)
Contrast ratios calculated using the standard W3C relative luminance formula ($L_1 + 0.05 / L_2 + 0.05$):

| Text / UI Element | Foreground Hex | Background Hex | Contrast Ratio | WCAG 2.1 AA Threshold | Result |
|---|---|---|---|---|---|
| Primary Body Text (`--text-strong`) | `#1F2D2D` | `#FFFFFF` | **14.27 : 1** | 4.5 : 1 (Normal Text) | **PASS** |
| Primary Body Text on Page BG | `#1F2D2D` | `#E8F3F3` | **12.60 : 1** | 4.5 : 1 (Normal Text) | **PASS** |
| Muted Subtitles & Labels (`--text-muted`) | `#5B6B6B` | `#FFFFFF` | **5.58 : 1** | 4.5 : 1 (Normal Text) | **PASS** |
| Muted Text on Page BG | `#5B6B6B` | `#E8F3F3` | **4.93 : 1** | 4.5 : 1 (Normal Text) | **PASS** |
| White Text on Primary Teal | `#FFFFFF` | `#1F7A74` | **5.13 : 1** | 4.5 : 1 (Normal Text) | **PASS** |
| Primary Teal on White | `#1F7A74` | `#FFFFFF` | **5.13 : 1** | 4.5 : 1 (Normal Text) | **PASS** |
| Normal Tier Status Text (`--ok-fg/bg`) | `#146C43` | `#E3F5EA` | **5.69 : 1** | 3.0 : 1 (Large / UI Component) | **PASS** |
| Watch Tier Status Text (`--warn-fg/bg`) | `#8A5300` | `#FFF1D6` | **5.67 : 1** | 3.0 : 1 (Large / UI Component) | **PASS** |
| Critical Tier Status Text (`--bad-fg/bg`) | `#B3261E` | `#FDE7E6` | **5.52 : 1** | 3.0 : 1 (Large / UI Component) | **PASS** |
| Solid Critical Alert (`--bad-solid`) | `#FFFFFF` | `#C62828` | **5.62 : 1** | 4.5 : 1 (Normal Text) | **PASS** |
| Accent Green Chip Ink | `#0F3D2E` | `#7AD672` | **6.77 : 1** | 3.0 : 1 (Large / UI Component) | **PASS** |
| Focus Ring Outline (`--focus-ring`) | `#0B5FFF` | `#FFFFFF` | **5.13 : 1** | 3.0 : 1 (UI Component) | **PASS** |
| Footer Disclaimer Text (`--text-muted`)| `#5B6B6B` | `#FFFFFF` | **5.58 : 1** | 4.5 : 1 (Normal Text) | **PASS** |

### B. Checklist Summary & Verification Evidence (A11Y-01 – A11Y-14)

| ID | WCAG Criterion | Evidence / Test Details | Result |
|---|---|---|---|
| **A11Y-01** | Token contrast ratios hold in rendered CSS | Computed contrast table verifies all ratios $\ge 4.5:1$ (normal) and $\ge 3:1$ (UI) from `tokens.css`. Lighthouse accessibility audit confirms 0 contrast warnings. | **PASS** |
| **A11Y-02** | Colour is never the only signal | Tier badges include text + SVG icon + border styling (`badge-elevated`, etc.). Charts use dashed vs solid strokes and distinctive circular markers. | **PASS** |
| **A11Y-03** | Full keyboard operability & focus order | MANUAL — No automated test in suite covers Tab sequence, skip link activation, or slider arrow-keys (test_at_23 tests preset button clicks). Verified manual checklist provided; pending user interactive completion. | **MANUAL** |
| **A11Y-04** | Visible focus indicators | `:focus-visible` defines `outline: 3px solid var(--focus-ring)` = `#0B5FFF`; `outline-offset: 2px` (contrast 5.13:1 against white). Verified via screenshot and keyboard tests. | **PASS** |
| **A11Y-05** | Semantic landmarks & single `<h1>` per route | Every route (S1–S6) validated via `test_a11y_05_landmarks_and_headings`: exactly 1 `<h1>` per view, with `header`, `aside`, `nav`, `main`, and `footer` landmarks. | **PASS** |
| **A11Y-06** | Focus moves on route change; unique `document.title` | `Router.navigate` moves focus to `h1` (`tabindex="-1"`) and updates `document.title` (e.g., `Forecast · CareCast`). Verified via `test_a11y_06_focus_management_on_route_change`. | **PASS** |
| **A11Y-07** | Data tables have `<caption>` and `<th scope="col">` | All table renderers create `<caption>` and `<th scope="col">`. Programmatic labels associated with inputs (`id`/`for` attributes). Verified in `test_a11y_07`. | **PASS** |
| **A11Y-08** | Charts: `figure/figcaption` and data-table alternatives | All charts wrap canvas in `<figure class="chart-figure">` with `<figcaption>` and collapsible `<details><table class="chart-alt-table">` raw data fallback. Verified in `test_a11y_08`. | **PASS** |
| **A11Y-09** | Dynamic announcements & busy states | `#live-announcer` (`aria-live="polite" aria-atomic="true"`) announces route changes. Errors use `role="alert"`. Loading states use `aria-busy="true"`. Verified in `test_a11y_09`. | **PASS** |
| **A11Y-10** | Minimum touch/target size $\ge 24\times24$ px (target 44 px) | Primary nav links: $44\text{ px}$ height; action buttons: $32\times32\text{ px}$; form inputs: $40\text{ px}$ height; skip link: $40\text{ px}$. | **PASS** |
| **A11Y-11** | Responsive reflow at 320 px without horizontal scroll | Verified via automated test `test_no_horizontal_body_scroll`: `document.body.scrollWidth <= window.innerWidth` across all 6 views at 320 px and 375 px. | **PASS** |
| **A11Y-12** | `prefers-reduced-motion` respected | `@media (prefers-reduced-motion: reduce)` sets all transition and animation durations to `0.01ms !important`. Zero flashing or pulsing animations. | **PASS** |
| **A11Y-13** | Valid `html[lang="en"]` and unique titles | `<!DOCTYPE html><html lang="en">` verified. All 6 views provide unique titles per `ROUTES` table. Verified in `test_a11y_13`. | **PASS** |
| **A11Y-14** | Form error identification in text | Threshold and surge inputs validate numeric boundaries, attach `.invalid` class, and display descriptive hint text. | **PASS** |

---

## 4. Responsive Fidelity (AT-41)

CareCast was rigorously tested across 6 viewport widths (320, 375, 768, 1024, 1280, 1440 px). Zero horizontal body scrolling occurs on any route.

| Viewport Width | Device Category | Layout Behavior | Body Scroll Width | Horizontal Scroll? |
|---|---|---|---|---|
| **320 px** | Minimum mobile (iPhone SE 1) | Single column; sidebar collapsed to off-canvas drawer; topbar chip hidden; table horizontal scroll container bounded; text word-break enabled | `320 px` | **NO (PASS)** |
| **375 px** | Standard mobile (iPhone 13/14) | Single column; drawer toggle visible; cards stacked with 12px padding | `375 px` | **NO (PASS)** |
| **768 px** | Tablet portrait (iPad Mini) | 2-column card flow; mobile drawer off-canvas; full chart figures | `768 px` | **NO (PASS)** |
| **1024 px** | Tablet landscape / Small laptop | 72px icon rail navigation; brand wordmark collapsed to icon | `1024 px` | **NO (PASS)** |
| **1280 px** | Standard desktop cockpit | Full 264px sidebar; complete 9/3 · 4/4/4 · 12 · 4/4/4 grid | `1280 px` | **NO (PASS)** |
| **1440 px** | Large desktop / Widescreen | Max-width content container (1440px) centered with comfortable margins | `1440 px` | **NO (PASS)** |

---

## 5. Visual Criteria Evaluation Table (VC-01 – VC-16)

| ID | Criterion Description | Status | Screenshot Reference | Deviation / Adaptation Reason |
|---|---|---|---|---|
| **VC-01** | Shell regions match reference (sidebar, topbar, breadcrumb with range field, content grid, footer) | **PASS** | `p6-s1-overview-1280.png` | None. All 5 shell regions rendered with matching spatial hierarchy. |
| **VC-02** | S1 row structure at $\ge 1280\text{ px}$ is 9/3 · 4/4/4 · 12 · 4/4/4 | **PASS** | `p6-s1-overview-1280.png` | None. Grid column spans match reference layout specification. |
| **VC-03** | Dominant palette = teal family on light blue-green page tint with white cards; rendered colours match tokens | **PASS** | `p6-s1-overview-1280.png` | None. `--primary-600: #1F7A74`, `--bg-page: #E8F3F3`, `--bg-surface: #FFFFFF` verified. |
| **VC-04** | Sidebar: brand block, outline icons, active item light-teal pill + filled icon tile, bottom teal info box | **PASS** | `p6-s1-overview-1280.png` | Adapted branding to CareCast; adapted emergency contact box to CDC Data & Disclaimer box linked to S6 per §2. |
| **VC-05** | Hero = solid teal banner, white text hierarchy (small $\rightarrow$ large $\rightarrow$ small), two light-green circular KPI chips | **PASS** | `p6-s1-overview-1280.png` | Adapted doctor schedule text to Weekly Planning Brief; KPI chips display forecast admissions and operational tier. |
| **VC-06** | Trend card is teal with white line and green circular markers | **PASS** | `p6-s1-overview-1280.png` | None. Renders recent 8-week admissions with circular point markers and percentage change badge. |
| **VC-07** | Watchlist rows show status pills (dot/icon + text) right-aligned | **PASS** | `p6-s1-overview-1280.png` | Adapted doctor roster into national respiratory disease watchlist (COVID-19, Influenza, RSV) per §2. |
| **VC-08** | Gauge is dashed teal arc with centred label and two bound pills beneath | **PASS** | `p6-s1-overview-1280.png` | Adapted consultation counter into capacity threshold gauge with Lower and Upper interval pills per §2. |
| **VC-09** | Forecast table has teal header, bold white text, bordered rows, and three icon action buttons per row | **PASS** | `p6-s1-overview-1280.png` | Adapted patient records into multi-horizon forecast schedule; action buttons open Explain, Scenario, and Details per §2. |
| **VC-10** | Charts use teal series on white cards, week labels on x-axis, light gridlines | **PASS** | `p6-s3-performance-1280.png` | None. Uses vendored Chart.js v4.4.7 with calibrated teal palette and dashed baseline curves. |
| **VC-11** | Capacity tiles use pale-tint background, circular icon, bold teal number | **PASS** | `p6-s1-overview-1280.png` | Adapted department tiles into Little's Law capacity illustration (Est. Beds, Staffed Beds, Nurse Shifts) per §2. |
| **VC-12** | Footer disclaimer visible on every screen | **PASS** | `p6-s1-overview-1280.png` through `p6-s6-data-1280.png` | None. Renders student project & non-clinical disclaimer footer across all 6 views. |
| **VC-13** | Card radius 8 px and padding 20 px ($\pm 2\text{ px}$) everywhere | **PASS** | `p6-s1-overview-1280.png` | None. Enforced via `--radius-md: 8px` and `--card-pad: 20px`. |
| **VC-14** | No Apollo name, logo, avatars, photos or illustration anywhere | **PASS** | All screenshots | None. Verified via automated string and DOM audits (`test_vc_14_no_apollo_or_fake_identities`). |
| **VC-15** | Honesty markers present: tier text+icon, SIMULATED/SCENARIO badges, disclaimers | **PASS** | `p6-s1-overview-1280.png`, `p6-s5-scenario-1280.png` | None. Verified via automated test `test_vc_15_honesty_markers_present`. |
| **VC-16** | One system font family; tabular numerals in tables/KPIs; scale per §3 | **PASS** | All screenshots | None. Uses system sans-serif font stack with `font-variant-numeric: tabular-nums`. |

---

## 6. Real Screenshot Audit Table (30 Files Captured in Prod Mode)

All screenshots captured from the real production-mode server using `scripts/capture_screenshots.py` against the real SQLite database (`data/carecast.db`). Verified with file size, dimensions, and SHA-256 checksums:

| Filename | Dimensions (W × H) | Size (bytes) | SHA-256 Checksum |
|---|---|---|---|
| `p6-s1-overview-320.png` | 320 × 3847 | 176,403 | `d455fff3c4f8a870ddfa89eb90f702907eb1f58902b10563a058af9803fef716` |
| `p6-s2-forecast-320.png` | 320 × 1933 | 96,846 | `f3fc98fe4cefff4faf7029ae6a9a10292c5ec006637b42c3c98ad6c18bd84abb` |
| `p6-s3-performance-320.png` | 320 × 1938 | 93,800 | `df52a1296ff56070388c5b481b726dd1a5d6bc66120168d8e8369d3073c492b1` |
| `p6-s4-explain-320.png` | 320 × 2573 | 103,068 | `f51a4b7efff4a438daa94f694b6f9bde8bfe12c33c4f6e96cf07c36d74a260df` |
| `p6-s5-scenario-320.png` | 320 × 2977 | 122,768 | `b21ac5fbe80dd0b028f124b481ecd30fee2f58396556cded091eb6a63ad7761f` |
| `p6-s6-data-320.png` | 320 × 5870 | 184,912 | `a50069b9d47106c898711ee67a29321142afb5fcbb4631739c081abeecfd9c19` |
| `p6-s1-overview-375.png` | 375 × 3660 | 178,122 | `4983cd1a686cc74f43e92d80b016d146f4e7cff58c88f01908ea1e17e6f553d9` |
| `p6-s2-forecast-375.png` | 375 × 1798 | 101,660 | `906c754dfead5ebe01342d40f72860e9b1c0a981ea374725be05c4fa324ee454` |
| `p6-s3-performance-375.png` | 375 × 1820 | 84,344 | `4373c0eadc9584d353a4ee9006e681148774c591d05e9ed6d03254e5204e7c85` |
| `p6-s4-explain-375.png` | 375 × 2471 | 103,997 | `fcaf0c53940e256bb0228ef8224b2617e9a7cbf7f74d9fcda57ed8c9eae18c1e` |
| `p6-s5-scenario-375.png` | 375 × 2783 | 124,969 | `bc6cdad0bb3d0bdd6dd6405c2801a366615b7c50d61128a583190ed0743cf5f5` |
| `p6-s6-data-375.png` | 375 × 5412 | 183,708 | `7a7f99e14e111f98fb1e985bf887c8fc4adc5753d56d1f35deff7a73ad510e58` |
| `p6-s1-overview-768.png` | 768 × 3383 | 215,536 | `1c866fa93b2567bf500b1cd85cda46e428c9f64903e55fa534197505bc590713` |
| `p6-s2-forecast-768.png` | 768 × 1566 | 134,430 | `8b80a14c8a604dfc4bfc783b9db234b9a518b3a047c595fe73a80652686f3fc2` |
| `p6-s3-performance-768.png` | 768 × 1588 | 101,321 | `4cd0340e9709dfabefe4abb64272a09742b62d455b439451e451de5c82f1e27a` |
| `p6-s4-explain-768.png` | 768 × 1381 | 113,169 | `54925a3ac49e3cc400d6ca42d28a819e11c7bcfdaba3d977c83903e40d3d5815` |
| `p6-s5-scenario-768.png` | 768 × 2577 | 159,415 | `ae407aace6f446a45b06cc8c1c398d90ab1733994edd29a5c7406c2e734aaa4b` |
| `p6-s6-data-768.png` | 768 × 4565 | 209,162 | `5085764959b3aa0674903f8ceb47dfdb93ba5983e02b51cc73dd634bf6cb5bfb` |
| `p6-s1-overview-1280.png` | 1280 × 1782 | 222,770 | `2541a51339dc9fe2a12ce33c7beeceed7d821cf6800f1113f1a43a1350af9ff6` |
| `p6-s2-forecast-1280.png` | 1280 × 1455 | 155,645 | `83c2b800f4c892cfb668b6ed983d23e85e91fd03ddaa98f3c81abe50f178d8f6` |
| `p6-s3-performance-1280.png` | 1280 × 1651 | 121,155 | `f3646d2c5c4f750a11ad482310af60d7f5be1e7d495aa292cfe2ae6e8f63ef24` |
| `p6-s4-explain-1280.png` | 1280 × 1361 | 132,064 | `83fe5d76511d42a020bb5cb8b9cca00c648af396c4d1e55b8db87a66426aeb1b` |
| `p6-s5-scenario-1280.png` | 1280 × 1822 | 172,838 | `0f660e8a2e1a654aa83e49f5fa27f6011a332619258bb6543537777ad9654677` |
| `p6-s6-data-1280.png` | 1280 × 4439 | 228,308 | `7485b6f189a5c0d12d7eb9438ad314569313f787c3df6e097da5c4ecba416877` |
| `p6-s1-overview-1440.png` | 1440 × 1791 | 224,804 | `8036e140003f77fb88a9d99e5f18cec4f0ad22c436a847ecebf74e88ad62c94f` |
| `p6-s2-forecast-1440.png` | 1440 × 1455 | 158,111 | `a7315f805ad9fa6f89015ee03b129715740e689a92dcce2e3af983fc82a3ee58` |
| `p6-s3-performance-1440.png` | 1440 × 1630 | 123,322 | `fdc3bf83b2779ae8bb4295c147595a8b528b4021d3e06251dfed45135dad684b` |
| `p6-s4-explain-1440.png` | 1440 × 1361 | 134,209 | `4ac6610f7037335fa9a97f190ca93360740db8a7146e87abfb6ab374e660bd72` |
| `p6-s5-scenario-1440.png` | 1440 × 1822 | 177,455 | `3bd23d0cd51d72d14ba586eff731625cced0c0b28dd224d57e40cc8c61802450` |
| `p6-s6-data-1440.png` | 1440 × 4418 | 231,365 | `f51b93ef4bedb2fdc87bd752e0c7b729f77cee0fb81b69bbe2c39cc5a62c6037` |

---

## 7. Security Audit Sign-Off (SR-5)

Incremental security review `reports/security/SR-5.md` was executed across all modified files. Authored by the agent; pending user review. Status: READY FOR USER REVIEW.
- **INC-01 (DOM Sinks):** Clean. 0 instances of dangerous HTML sinks.
- **INC-02 (CSP):** Clean. Strict CSP with 0 inline styles and 0 external fonts/CDNs.
- **INC-03 (Vendored Packages):** Pinned Chart.js v4.4.7 verified against npm SHA-256; 0 vulnerabilities.
- **INC-04 (Local State):** `localStorage` safely bounded in `try/catch`.
- **INC-05 (URL Hash Params):** Defensive validation against database enumeration values.
- **INC-06 (Lifecycle & Memory):** Clean view teardown and systematic `chart.destroy()`.

---

## 8. Gate Decisions Required from User

As mandated by Rule G-0 and Phase 6 instructions, I am stopping here and awaiting:

1. **Your Approval Token:**
   > `"APPROVED: PHASE 6"`

2. **Decision OD-05 (Feature F13 Scope):**
   - **Context:** Feature F13 covers hierarchical subnational / state-level modeling (50 states + DC + territories).
   - **Question:** Do you want to **attempt F13** (expanding the model pipeline and UI selectors to subnational state data), or **keep the current national-level scope (US)** as specified for the MVP?

3. **Decision OD-04 (Deployment Target for Phase 7):**
   - **Context:** Phase 7 packages the application for production deployment, reproducible verification, and distribution.
   - **Question:** What is your preferred target:
     - **Option A:** Single self-contained Docker container (e.g., for Google Cloud Run / AWS ECS / local Docker compose).
     - **Option B:** Standalone native Python executable / virtualenv package with systemd/service unit.
     - **Option C:** Dual static frontend (CDN / Nginx) + headless FastAPI container.
