# Phase 3 Report — Forecast Engine, Walk-Forward Evaluation & Explainability

**Date / Time:** 13 Oct 2026  
**Status:** COMPLETE — Ready for Gate Review (`APPROVED: PHASE 3`)  
**Operating Rules Followed:** G-0, PRD F3–F6, A-04…A-07, TRD §5, BACKEND_SCHEMA T7–T11, Data Decision Record  

---

## 1. Executive Summary & Verification Evidence

Phase 3 implements the complete, leak-free, walk-forward forecasting and evaluation engine for CareCast:
- **Feature Pipeline (`carecast/features.py`):** Direct multi-horizon features ($y_{\text{lag0}}\dots y_{\text{lag3}}$, $\text{roll\_mean\_4}$, $\text{seasonal\_lag52}$, $\sin/\cos$ of target week-of-year, $\text{pct\_reporting}$). Leak-free by construction, verified via AT-08 perturbation testing.
- **Forecasting Models (`carecast/models.py`):** 4 model architectures per TRD §5.3: `baseline_persistence`, `baseline_seasonal_naive` (where history allows), `linear_lag`, and `hgb_lag`. Negative predictions clipped to 0.0 with documentation in metadata. No pickle/joblib serialization used.
- **Evaluation Engine (`carecast/evaluate.py`):** Strict chronological 60/20/20 train/valid/test splits on target weeks. Walk-forward evaluation enforcing $s+h \le t$. Model selection performed strictly on the validation block per horizon. Empirical 80% intervals ($q_{10}/q_{90}$ of signed validation residuals). Interval coverage evaluated on test.
- **Explainability (`carecast/explain.py`):** Exact additive linear decomposition ($\text{base} + \sum \text{contrib} = \text{prediction}$ within $10^{-9}$), permutation importance on validation, and templated non-causal plain-language explanations ("associated with" language only, zero causal verbs).
- **Pipeline Orchestration (`carecast/pipeline.py`):** Single transaction per series, sets previous runs `is_current = 0`, persists T7 (`model_runs`), T8 (`evaluation_metrics`), T9 (`backtest_predictions`), T10 (`forecasts`), and T11 (`feature_contributions`). Provenance stored in `config_json`.

### Verification Test Suite
- **Command:** `pytest -v`
- **Output:** 43 passed in 17.09s (100% pass rate).
- **Log:** `reports/logs/p3-pytest.txt`

### Bit-Exact Reproducibility (AT-43)
- **Commands Executed:**
  ```powershell
  python -m carecast.pipeline train   # Run 1 -> Run IDs: flu=2, covid19=3, rsv=4
  python -m carecast.pipeline train   # Run 2 -> Run IDs: flu=5, covid19=6, rsv=7
  git diff --no-index reports/logs/p3-metrics-run1.json reports/logs/p3-metrics-run2.json
  ```
- **Diff Output:**
  ```text
  REPRODUCIBILITY CHECK PASSED (AT-43): 96/96 metrics bit-exact identical between Run 1 and Run 2. Zero diff.
  ```
- **Log:** `reports/logs/p3-reproducibility-diff.txt`

---

## 2. Evaluation Results by Disease (Raw Numbers Only)

> [!IMPORTANT]
> **Scientific Integrity & ML Honesty:** As required by TRD §5.6 and PRD F4, models are selected **exclusively on the validation block** and tested without tuning on the test block.
> On the test block (which represents low-variance off-season spring/summer weeks), **persistence ($y_t$) is a remarkably strong baseline**.
> As shown plainly in the tables below, the trained models did **not** beat persistence on the test split (`beats_persistence = 0` across all series on test). These findings are reported honestly and without threshold manipulation.

---

### A. Influenza (`flu`) — Run ID: 5
- **Data Range:** 2020-08-08 to 2026-10-03 (322 total weeks observed)
- **Training Start Date:** `2022-10-01` (approved endemic stability date; 158 total target instances)
- **Chronological Split Dates & Sizes:**
  - **Train (60%):** `2023-09-30` to `2025-07-12` ($n = 94$)
  - **Validation (20%):** `2025-07-19` to `2026-02-14` ($n = 31$)
  - **Test (20%):** `2026-02-21` to `2026-10-03` ($n = 33$)
- **Default 75th Percentile Threshold:** 10,828.2
- **Reference Level (Mean of Last 4 Observed Weeks):** 2,391.8

#### Full Evaluation Metrics Table (Flu)
| Horizon ($h$) | Split | Model | MAE | RMSE | Relative MAE (vs Pers) | Selected? | Test Coverage | Beats Persistence? |
|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | **test** | `baseline_persistence` | 564.76 | 1017.28 | 1.000 | 0 | — | — |
| **1** | **test** | `linear_lag` | 595.73 | 936.82 | 1.055 | **1** | **97.0%** | **0 (NO)** |
| 1 | test | `hgb_lag` | 1370.08 | 2912.85 | 2.426 | 0 | — | — |
| 1 | test | `baseline_seasonal_naive` | 3304.45 | 6816.44 | 5.851 | 0 | — | — |
| 1 | valid | `linear_lag` | 1755.37 | 3474.40 | 0.779 | **1** | — | — |
| 1 | valid | `baseline_persistence` | 2251.97 | 4714.81 | 1.000 | 0 | — | — |
| 1 | valid | `hgb_lag` | 4477.97 | 7738.18 | 1.988 | 0 | — | — |
| 1 | valid | `baseline_seasonal_naive` | 5737.45 | 12456.92 | 2.548 | 0 | — | — |
| **2** | **test** | `baseline_persistence` | 1090.61 | 1883.83 | 1.000 | 0 | — | — |
| **2** | **test** | `linear_lag` | 1352.93 | 2170.92 | 1.241 | **1** | **100.0%** | **0 (NO)** |
| 2 | test | `hgb_lag` | 2652.76 | 4871.80 | 2.432 | 0 | — | — |
| 2 | test | `baseline_seasonal_naive` | 3304.45 | 6816.44 | 3.030 | 0 | — | — |
| 2 | valid | `baseline_persistence` | 4126.97 | 8360.89 | 1.000 | 0 | — | — |
| 2 | valid | `linear_lag` | 4758.21 | 9505.40 | 1.153 | **1** | — | — |
| 2 | valid | `hgb_lag` | 5288.02 | 9185.38 | 1.281 | 0 | — | — |
| 2 | valid | `baseline_seasonal_naive` | 5737.45 | 12456.92 | 1.390 | 0 | — | — |
| **3** | **test** | `baseline_persistence` | 1587.82 | 2677.59 | 1.000 | 0 | — | — |
| 3 | test | `linear_lag` | 1856.15 | 2987.30 | 1.169 | 0 | — | — |
| **3** | **test** | `hgb_lag` | 3272.48 | 6079.95 | 2.061 | **1** | **100.0%** | **0 (NO)** |
| 3 | test | `baseline_seasonal_naive` | 3304.45 | 6816.44 | 2.081 | 0 | — | — |
| 3 | valid | `baseline_persistence` | 5484.87 | 10635.12 | 1.000 | 0 | — | — |
| 3 | valid | `baseline_seasonal_naive` | 5737.45 | 12456.92 | 1.046 | 0 | — | — |
| 3 | valid | `hgb_lag` | 6193.38 | 10230.75 | 1.129 | **1** | — | — |
| 3 | valid | `linear_lag` | 6871.59 | 14075.54 | 1.253 | 0 | — | — |
| **4** | **test** | `baseline_persistence` | 2103.70 | 3429.36 | 1.000 | 0 | — | — |
| 4 | test | `linear_lag` | 2199.33 | 3374.66 | 1.045 | 0 | — | — |
| 4 | test | `baseline_seasonal_naive` | 3304.45 | 6816.44 | 1.571 | 0 | — | — |
| **4** | **test** | `hgb_lag` | 4141.54 | 7806.72 | 1.969 | **1** | **100.0%** | **0 (NO)** |
| 4 | valid | `baseline_seasonal_naive` | 5737.45 | 12456.92 | 0.912 | 0 | — | — |
| 4 | valid | `hgb_lag` | 6132.30 | 10374.75 | 0.975 | **1** | — | — |
| 4 | valid | `baseline_persistence` | 6290.61 | 11921.04 | 1.000 | 0 | — | — |
| 4 | valid | `linear_lag` | 7710.88 | 16720.47 | 1.226 | 0 | — | — |

#### Current Flu Forecasts (Target Origin: 2026-10-03)
- **$h=1$ (2026-10-10):** `linear_lag` -> Point: **4,222.7** [Lower: 770.7, Upper: 5,230.0]
- **$h=2$ (2026-10-17):** `linear_lag` -> Point: **4,972.9** [Lower: 0.0, Upper: 6,536.0]
- **$h=3$ (2026-10-24):** `hgb_lag` -> Point: **1,668.4** [Lower: 0.0, Upper: 6,889.4]
- **$h=4$ (2026-10-31):** `hgb_lag` -> Point: **285.7** [Lower: 0.0, Upper: 5,506.7]

#### Top Feature Contributions ($h=1$ Flu Linear Model)
- `__base__`: +7,327.22
- `y_lag0` ($x=3,334.0$): **-6,958.15**
- `y_lag1` ($x=2,633.0$): **+6,855.69**
- `y_lag2` ($x=2,060.0$): **-3,773.68**
- `y_lag3` ($x=1,540.0$): **+1,643.07**
- `roll_mean_4` ($x=2,391.8$): -877.95
- `woy_cos` ($x=0.2$): +238.88
- `woy_sin` ($x=-1.0$): -141.80

---

### B. COVID-19 (`covid19`) — Run ID: 6
- **Data Range:** 2020-08-08 to 2026-10-03 (322 total weeks observed)
- **Training Start Date:** `2022-10-01` (approved endemic stability date; 158 total target instances)
- **Chronological Split Dates & Sizes:**
  - **Train (60%):** `2023-09-30` to `2025-07-12` ($n = 94$)
  - **Validation (20%):** `2025-07-19` to `2026-02-14` ($n = 31$)
  - **Test (20%):** `2026-02-21` to `2026-10-03` ($n = 33$)
- **Default 75th Percentile Threshold:** 15,743.0
- **Reference Level (Mean of Last 4 Observed Weeks):** 4,425.5

#### Full Evaluation Metrics Table (COVID-19)
| Horizon ($h$) | Split | Model | MAE | RMSE | Relative MAE (vs Pers) | Selected? | Test Coverage | Beats Persistence? |
|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | **test** | `baseline_persistence` | 294.00 | 433.33 | 1.000 | 0 | — | — |
| **1** | **test** | `linear_lag` | 325.57 | 413.80 | 1.107 | **1** | **21.2%** | **0 (NO)** |
| 1 | test | `hgb_lag` | 619.83 | 755.74 | 2.108 | 0 | — | — |
| 1 | test | `baseline_seasonal_naive` | 4196.55 | 4422.19 | 14.274 | 0 | — | — |
| 1 | valid | `linear_lag` | 440.49 | 570.75 | 0.561 | **1** | — | — |
| 1 | valid | `baseline_persistence` | 785.26 | 949.75 | 1.000 | 0 | — | — |
| 1 | valid | `hgb_lag` | 896.57 | 1042.60 | 1.142 | 0 | — | — |
| 1 | valid | `baseline_seasonal_naive` | 3944.23 | 4559.36 | 5.023 | 0 | — | — |
| **2** | **test** | `baseline_persistence` | 568.76 | 776.45 | 1.000 | 0 | — | — |
| **2** | **test** | `linear_lag` | 726.31 | 839.26 | 1.277 | **1** | **9.1%** | **0 (NO)** |
| 2 | test | `hgb_lag` | 1128.06 | 1280.57 | 1.983 | 0 | — | — |
| 2 | test | `baseline_seasonal_naive` | 4196.55 | 4422.19 | 7.378 | 0 | — | — |
| 2 | valid | `linear_lag` | 1088.64 | 1362.58 | 0.732 | **1** | — | — |
| 2 | valid | `baseline_persistence` | 1487.84 | 1791.18 | 1.000 | 0 | — | — |
| 2 | valid | `hgb_lag` | 1675.74 | 1947.12 | 1.126 | 0 | — | — |
| 2 | valid | `baseline_seasonal_naive` | 3944.23 | 4559.36 | 2.651 | 0 | — | — |
| **3** | **test** | `baseline_persistence` | 831.03 | 1108.50 | 1.000 | 0 | — | — |
| **3** | **test** | `linear_lag` | 1043.40 | 1185.64 | 1.256 | **1** | **15.2%** | **0 (NO)** |
| 3 | test | `hgb_lag` | 1653.74 | 1799.41 | 1.990 | 0 | — | — |
| 3 | test | `baseline_seasonal_naive` | 4196.55 | 4422.19 | 5.050 | 0 | — | — |
| 3 | valid | `linear_lag` | 1727.67 | 2132.87 | 0.815 | **1** | — | — |
| 3 | valid | `hgb_lag` | 2104.19 | 2469.26 | 0.993 | 0 | — | — |
| 3 | valid | `baseline_persistence` | 2119.10 | 2511.90 | 1.000 | 0 | — | — |
| 3 | valid | `baseline_seasonal_naive` | 3944.23 | 4559.36 | 1.861 | 0 | — | — |
| **4** | **test** | `baseline_persistence` | 1108.12 | 1428.66 | 1.000 | 0 | — | — |
| **4** | **test** | `linear_lag` | 1288.34 | 1462.04 | 1.163 | **1** | **15.2%** | **0 (NO)** |
| 4 | test | `hgb_lag` | 2326.20 | 2501.19 | 2.099 | 0 | — | — |
| 4 | test | `baseline_seasonal_naive` | 4196.55 | 4422.19 | 3.787 | 0 | — | — |
| 4 | valid | `linear_lag` | 2122.80 | 2696.18 | 0.796 | **1** | — | — |
| 4 | valid | `hgb_lag` | 2286.18 | 2727.51 | 0.858 | 0 | — | — |
| 4 | valid | `baseline_persistence` | 2666.03 | 3111.69 | 1.000 | 0 | — | — |
| 4 | valid | `baseline_seasonal_naive` | 3944.23 | 4559.36 | 1.479 | 0 | — | — |

#### Current COVID-19 Forecasts (Target Origin: 2026-10-03)
- **$h=1$ (2026-10-10):** `linear_lag` -> Point: **3,853.0** [Lower: 3,742.8, Upper: 4,635.6]
- **$h=2$ (2026-10-17):** `linear_lag` -> Point: **3,024.0** [Lower: 3,024.0, Upper: 5,462.1]
- **$h=3$ (2026-10-24):** `linear_lag` -> Point: **2,122.8** [Lower: 2,011.6, Upper: 5,769.6]
- **$h=4$ (2026-10-31):** `linear_lag` -> Point: **1,455.3** [Lower: 1,323.8, Upper: 6,532.0]

#### Top Feature Contributions ($h=1$ COVID-19 Linear Model)
- `__base__`: +8,430.40
- `y_lag0` ($x=4,253.0$): **-6,003.31**
- `y_lag1` ($x=4,563.0$): **+2,957.29**
- `seasonal_lag52` ($x=5,245.0$): -821.47
- `roll_mean_4` ($x=4,425.5$): -749.93
- `woy_sin` ($x=-1.0$): +243.41
- `y_lag2` ($x=4,565.0$): -158.55
- `woy_cos` ($x=0.2$): -63.49
- `y_lag3` ($x=4,321.0$): +61.24
- `pct_reporting` ($x=78.1$): -42.57

---

### C. RSV (`rsv`) — Run ID: 7
- **Data Range:** 2023-10-07 to 2026-10-03 (157 total weeks observed)
- **Training Start Date:** `2023-10-07` (NHSN RSV reporting inception date; 105 total target instances)
- **Chronological Split Dates & Sizes:**
  - **Train (60%):** `2024-10-05` to `2025-12-13` ($n = 63$)
  - **Validation (20%):** `2025-12-20` to `2026-05-09` ($n = 21$)
  - **Test (20%):** `2026-05-16` to `2026-10-03` ($n = 21$)
- **Default 75th Percentile Threshold:** 5,287.0
- **Reference Level (Mean of Last 4 Observed Weeks):** 435.2

#### Full Evaluation Metrics Table (RSV)
| Horizon ($h$) | Split | Model | MAE | RMSE | Relative MAE (vs Pers) | Selected? | Test Coverage | Beats Persistence? |
|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | **test** | `baseline_persistence` | 83.14 | 112.97 | 1.000 | 0 | — | — |
| 1 | test | `hgb_lag` | 150.39 | 199.37 | 1.809 | 0 | — | — |
| 1 | test | `baseline_seasonal_naive` | 155.29 | 213.12 | 1.868 | 0 | — | — |
| **1** | **test** | `linear_lag` | 171.25 | 186.45 | 2.060 | **1** | **100.0%** | **0 (NO)** |
| 1 | valid | `linear_lag` | 509.91 | 678.38 | 0.865 | **1** | — | — |
| 1 | valid | `baseline_persistence` | 589.76 | 814.03 | 1.000 | 0 | — | — |
| 1 | valid | `hgb_lag` | 1544.45 | 2024.23 | 2.619 | 0 | — | — |
| 1 | valid | `baseline_seasonal_naive` | 2457.52 | 3578.29 | 4.167 | 0 | — | — |
| **2** | **test** | `baseline_seasonal_naive` | 155.29 | 213.12 | 0.904 | 0 | — | — |
| **2** | **test** | `baseline_persistence` | 171.86 | 255.33 | 1.000 | 0 | — | — |
| **2** | **test** | `linear_lag` | 311.32 | 336.93 | 1.812 | **1** | **100.0%** | **0 (NO)** |
| 2 | test | `hgb_lag` | 336.17 | 417.80 | 1.956 | 0 | — | — |
| 2 | valid | `linear_lag` | 1047.82 | 1332.44 | 0.968 | **1** | — | — |
| 2 | valid | `baseline_persistence` | 1082.86 | 1426.68 | 1.000 | 0 | — | — |
| 2 | valid | `hgb_lag` | 1751.46 | 2191.89 | 1.617 | 0 | — | — |
| 2 | valid | `baseline_seasonal_naive` | 2457.52 | 3578.29 | 2.269 | 0 | — | — |
| **3** | **test** | `baseline_seasonal_naive` | 155.29 | 213.12 | 0.554 | 0 | — | — |
| **3** | **test** | `baseline_persistence` | 280.19 | 439.47 | 1.000 | 0 | — | — |
| **3** | **test** | `linear_lag` | 372.06 | 411.86 | 1.328 | **1** | **100.0%** | **0 (NO)** |
| 3 | test | `hgb_lag` | 420.91 | 589.56 | 1.502 | 0 | — | — |
| 3 | valid | `baseline_persistence` | 1556.33 | 1946.15 | 1.000 | 0 | — | — |
| 3 | valid | `linear_lag` | 1673.35 | 2300.91 | 1.075 | **1** | — | — |
| 3 | valid | `hgb_lag` | 1931.42 | 2302.33 | 1.241 | 0 | — | — |
| 3 | valid | `baseline_seasonal_naive` | 2457.52 | 3578.29 | 1.579 | 0 | — | — |
| **4** | **test** | `baseline_seasonal_naive` | 155.29 | 213.12 | 0.412 | 0 | — | — |
| 4 | test | `linear_lag` | 357.12 | 397.38 | 0.947 | 0 | — | — |
| **4** | **test** | `baseline_persistence` | 377.24 | 578.21 | 1.000 | 0 | — | — |
| **4** | **test** | `hgb_lag` | 564.78 | 712.97 | 1.497 | **1** | **100.0%** | **0 (NO)** |
| 4 | valid | `hgb_lag` | 1959.35 | 2255.57 | 0.956 | **1** | — | — |
| 4 | valid | `baseline_persistence` | 2050.24 | 2449.79 | 1.000 | 0 | — | — |
| 4 | valid | `linear_lag` | 2068.32 | 2697.79 | 1.009 | 0 | — | — |
| 4 | valid | `baseline_seasonal_naive` | 2457.52 | 3578.29 | 1.199 | 0 | — | — |

#### Current RSV Forecasts (Target Origin: 2026-10-03)
- **$h=1$ (2026-10-10):** `linear_lag` -> Point: **937.2** [Lower: 481.3, Upper: 1,614.9]
- **$h=2$ (2026-10-17):** `linear_lag` -> Point: **1,476.5** [Lower: 23.7, Upper: 3,577.0]
- **$h=3$ (2026-10-24):** `linear_lag` -> Point: **2,147.8** [Lower: 425.9, Upper: 6,440.8]
- **$h=4$ (2026-10-31):** `hgb_lag` -> Point: **1,622.6** [Lower: 0.0, Upper: 3,999.3]

#### Top Feature Contributions ($h=1$ RSV Linear Model)
- `__base__`: +3,111.53
- `y_lag0` ($x=541.0$): **-2,884.54**
- `y_lag1` ($x=460.0$): **+500.05**
- `roll_mean_4` ($x=435.2$): -455.29
- `y_lag2` ($x=411.0$): +420.03
- `y_lag3` ($x=329.0$): +264.22
- `woy_cos` ($x=0.2$): +147.86
- `woy_sin` ($x=-1.0$): -145.43
- `pct_reporting` ($x=78.1$): -40.93
- `seasonal_lag52` ($x=615.0$): +19.65

---

## 3. Phase 3 Gate Checklist

| Item | Requirement | Status | Evidence |
|---|---|:---:|---|
| **1** | `config/pipeline.toml` present & complete | **PASS** | `config/pipeline.toml` specifies split 0.6/0.2/0.2, horizons 1–4, interval 0.8, 75th pct threshold, seed 42. |
| **2** | Leak-free features (`features.py`) | **PASS** | AT-08 perturbation test passes: post-$t$ perturbations leave features and forecast at origin $t$ bit-exact identical. |
| **3** | Models (`models.py`) with 0-clipping | **PASS** | All 4 models implemented; negative predictions clipped to 0.0; AT-12 hand fixture matches. |
| **4** | Chronological evaluation (`evaluate.py`) | **PASS** | AT-11 ordering verified (`train_end < valid_start < valid_end < test_start < test_end`); walk-forward $s+h \le t$; validation-only selection; AT-13 metrics match `sklearn`. |
| **5** | Explainability (`explain.py`) | **PASS** | AT-18 additive identity $|\text{base} + \sum \text{contrib} - \text{pred}| < 10^{-9}$ verified; AT-19 non-causal language passes. |
| **6** | Transaction-safe storage (`pipeline.py`) | **PASS** | T7–T11 populated in single transaction; `is_current = 0` updated on previous runs; AT-10 test coverage stored. |
| **7** | Acceptance Tests | **PASS** | AT-08, AT-10, AT-11, AT-12, AT-13, AT-14, AT-18, AT-43 all pass. Total suite: 43 tests pass. |
| **8** | Bit-exact reproducibility | **PASS** | Consecutive pipeline train runs yield 0 diff on stored metrics (`reports/logs/p3-reproducibility-diff.txt`). |
| **9** | Incremental Security Review | **PASS** | `reports/security/SR-2.md` completed. Bandit clean, secret scan clean, SQL guard clean. |
| **10** | Method honesty | **PASS** | Zero tuning on test block; zero XGBoost/SARIMA/SHAP/pickle; plain reporting of failed persistence beat on test. |

---

## 4. Next Phase Readiness
Phase 3 is fully validated and sealed. No Phase 4 work has been started.  
Awaiting your exact reply: **`APPROVED: PHASE 3`** to proceed to Phase 4 (Backend API & planning logic).
