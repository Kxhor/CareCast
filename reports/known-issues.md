# CareCast — Known Issues Register

**Audit Standard:** Strict Rule G-0 & Scientific Honesty  
**Date:** 2026-10-14  
**Status:** Documented and Disclosed (FLAGGED ONLY — NOT FIXED per Master Prompt)

This document tracks disclosed technical limitations and anomalies identified during the Phase 7 comprehensive audit. Per master audit rules, these items are flagged with detailed diagnostic evidence and recommended fixes, but are left unmodified in the codebase.

---

## Issue 1 (Item 8): Prediction Interval Empirical Miscalibration

- **Affected Components:** `carecast/evaluate.py`, `carecast/models.py`, `/api/v1/forecast`, `/api/v1/evaluation`
- **Severity:** Medium (Statistical / Decision-Support)
- **Observed Evidence:**
  The nominal prediction interval target is 80% coverage, computed via empirical quantiles ($q_{10}$ and $q_{90}$) of signed residuals on the chronological validation block.
  On the held-out test block, empirical coverage diverges substantially from nominal 80%:
  - **Influenza:**
    - Horizon 1: **97.0%**
    - Horizon 2: **100.0%**
    - Horizon 3: **100.0%**
    - Horizon 4: **100.0%**
    *(Over-conservative / wide intervals on spring/summer off-season).*
  - **COVID-19:**
    - Horizon 1: **21.2%**
    - Horizon 2: **9.1%**
    - Horizon 3: **15.2%**
    - Horizon 4: **15.2%**
    *(Severe under-coverage / under-calibration due to non-stationary trend shift from validation winter surge to low test baseline).*
  - **RSV:**
    - Horizon 1: **100.0%**
    - Horizon 2: **100.0%**
    - Horizon 3: **100.0%**
    - Horizon 4: **100.0%**
    *(Over-conservative on low summer endemic base).*
- **Root Cause:**
  Static residual quantiles from a single seasonal validation split cannot accommodate multi-year regime shifts and epidemiological volatility between winter peaks and summer troughs.
- **Recommended Fix (Do Not Apply):**
  1. Replace static residual quantiles with Conformalized Quantile Regression (CQR) or rolling multi-season empirical error pools.
  2. Implement season-conditional interval bands (separate winter surge variance estimates from summer trough variance estimates).

---

## Issue 2 (Item 10): Data Quality Issues List Truncation in `/api/v1/meta` [FIXED]

- **Affected Components:** `carecast/api/routes.py` (line 356), `MetaResponse.quality_issues`
- **Severity:** Low (Informational / Completeness)
- **Status:** **FIXED** (Task T4). Limit raised to `LIMIT 500` in `carecast/api/routes.py`. All 165 rows returned; verified via `tests/test_t4_quality_count.py`.
- **Observed Evidence:**
  Querying `/api/v1/meta` initially returned exactly 50 entries in `quality_issues`, truncating 115 rows from the database table `data_quality_issues` (165 rows).
- **Resolution:**
  Changed query to `LIMIT 500`. Test `tests/test_t4_quality_count.py` asserts that `len(quality_issues) == 165`. OpenAPI snapshot SHA-256 remains intact.

---

## Issue 3 (Item 11): Multi-byte UTF-8 Em-Dash in Disclaimer Strings

- **Affected Components:** `config/planning.toml` (line 12), `carecast/api/routes.py` (line 329), `/api/v1/meta`
- **Severity:** Low (Encoding Compatibility / Interoperability)
- **Status:** Documented / Handled. Verified `<meta charset="UTF-8">` present in `web/index.html` and UTF-8 roundtrip verified via `tests/test_t5_utf8.py`.
- **Observed Evidence:**
  The `note` field in `defaults.capacity` is defined as:
  ```toml
  note = "DEMO PLACEHOLDER — not data"
  ```
  The separator between "PLACEHOLDER" and "not data" is a Unicode EM DASH (`U+2014`, bytes `\xe2\x80\x94`).
  While fully compliant in UTF-8 environments, clients or environments that open JSON responses in default Windows-1252/cp1252 encodings without explicit `encoding="utf-8"` encounter mojibake (`â€”`) or `UnicodeDecodeError`.
- **Root Cause:**
  Usage of non-ASCII punctuation (`—`) instead of standard ASCII hyphen-minus (`-`).
- **Recommended Fix (Do Not Apply):**
  1. Replace `"DEMO PLACEHOLDER — not data"` with the ASCII equivalent `"DEMO PLACEHOLDER - not data"`.
  2. Ensure all API responses include `content-type: application/json; charset=utf-8`.

---

## Issue 4: All Current Alerts Evaluate to Normal Tier

- **Affected Components:** `carecast/planning.py`, `/api/v1/forecast`, Overview & Forecast UI (S1, S2)
- **Severity:** Informational (Data Context / Operational Appearance)
- **Status:** Documented / Expected for current temporal snapshot.
- **Observed Evidence:**
  In the current dataset snapshot (`as_of_date: 2024-04-27` / spring season), all three tracked pathogens (COVID-19, Influenza, RSV) evaluate to the `"normal"` tier across all horizons (h=1..4). No pathogens currently trigger `"watch"` or `"elevated"`.
- **Root Cause:**
  The CDC historical training set spans high winter surge seasons (e.g. 2022-2023 and 2023-2024 peaks), making the 75th percentile threshold relatively high. The latest available test observations fall in late spring (April 2024), where seasonal respiratory admissions are near annual baselines. Thus, point forecasts and upper 80% interval bounds remain below the 75th percentile threshold.
- **Notes for Reviewers:**
  This is epidemically accurate behavior for spring data, not a software defect. Watch and Elevated states can be observed and tested using S5 (Scenario Modeling) by applying positive surge percentages (e.g. +20% to +50%), or in unit tests with synthetic threshold overrides.

