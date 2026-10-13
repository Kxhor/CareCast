"""Feature engineering for time-series admission forecasting (Phase 3).

Constructs leak-free feature matrices at origin t for direct multi-horizon forecasting (h = 1..4).
Features conform to TRD §5.2:
- y_lag0, y_lag1, y_lag2, y_lag3
- roll_mean_4: mean(y_lag0..y_lag3)
- seasonal_lag52: y at target_date - 52 weeks (only if history allows)
- woy_sin, woy_cos: sine/cosine of the TARGET week-of-year
- pct_reporting: hospital reporting coverage at origin t
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any
import numpy as np
import pandas as pd


def compute_woy_cyclical(target_date: date | str) -> tuple[float, float]:
    """Compute (woy_sin, woy_cos) for the target week-of-year."""
    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date)
    woy = target_date.isocalendar().week
    # Standard 52-week annual cycle
    angle = 2.0 * math.pi * (woy / 52.0)
    return float(np.sin(angle)), float(np.cos(angle))


def build_feature_row(
    series_df: pd.DataFrame,
    origin_idx: int,
    h: int,
    target_col: str = "admissions_count",
    include_seasonal_lag52: bool = True,
    include_pct_reporting: bool = True,
) -> dict[str, Any] | None:
    """Build a single feature dict at origin t (origin_idx) for horizon h.

    Returns None if insufficient history precedes origin t.
    """
    if origin_idx < 3:
        # Need at least 4 observations for lag0..lag3 and roll_mean_4
        return None

    row_t = series_df.iloc[origin_idx]
    origin_date_str = row_t["week_end_date"]
    origin_date = date.fromisoformat(origin_date_str)
    target_date = origin_date + timedelta(weeks=h)
    target_date_str = target_date.isoformat()

    # Lags at origin t (strictly <= origin_idx)
    y_lag0 = float(series_df.iloc[origin_idx][target_col])
    y_lag1 = float(series_df.iloc[origin_idx - 1][target_col])
    y_lag2 = float(series_df.iloc[origin_idx - 2][target_col])
    y_lag3 = float(series_df.iloc[origin_idx - 3][target_col])
    roll_mean_4 = float((y_lag0 + y_lag1 + y_lag2 + y_lag3) / 4.0)

    woy_sin, woy_cos = compute_woy_cyclical(target_date)

    feat: dict[str, Any] = {
        "y_lag0": y_lag0,
        "y_lag1": y_lag1,
        "y_lag2": y_lag2,
        "y_lag3": y_lag3,
        "roll_mean_4": roll_mean_4,
        "woy_sin": woy_sin,
        "woy_cos": woy_cos,
    }

    if include_pct_reporting and "pct_reporting" in series_df.columns:
        pct_val = row_t.get("pct_reporting")
        feat["pct_reporting"] = float(pct_val) if pd.notna(pct_val) else 90.0

    if include_seasonal_lag52:
        target_minus_52 = (target_date - timedelta(weeks=52)).isoformat()
        # Find observation at target_minus_52 in data <= origin_idx
        prev_rows = series_df.iloc[: origin_idx + 1]
        match = prev_rows[prev_rows["week_end_date"] == target_minus_52]
        if not match.empty and pd.notna(match.iloc[0][target_col]):
            feat["seasonal_lag52"] = float(match.iloc[0][target_col])
        else:
            # Cannot compute seasonal_lag52 for this origin
            return None

    return feat


def create_dataset_for_horizon(
    df: pd.DataFrame,
    h: int,
    target_col: str = "admissions_count",
    include_seasonal_lag52: bool = False,
    include_pct_reporting: bool = True,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """Build (X, y, meta) for horizon h across all valid origins.

    meta contains origin_week_end_date and target_week_end_date.
    """
    df_sorted = df.sort_values("week_end_date").reset_index(drop=True)
    n = len(df_sorted)

    rows_x = []
    rows_y = []
    rows_meta = []

    date_to_y = dict(zip(df_sorted["week_end_date"], df_sorted[target_col]))

    for idx in range(n):
        origin_date_str = df_sorted.iloc[idx]["week_end_date"]
        origin_date = date.fromisoformat(origin_date_str)
        target_date_str = (origin_date + timedelta(weeks=h)).isoformat()

        # Target must exist in the dataset to evaluate/train
        if target_date_str not in date_to_y or pd.isna(date_to_y[target_date_str]):
            continue

        feat = build_feature_row(
            df_sorted,
            origin_idx=idx,
            h=h,
            target_col=target_col,
            include_seasonal_lag52=include_seasonal_lag52,
            include_pct_reporting=include_pct_reporting,
        )
        if feat is None:
            continue

        rows_x.append(feat)
        rows_y.append(float(date_to_y[target_date_str]))
        rows_meta.append({
            "origin_week_end_date": origin_date_str,
            "target_week_end_date": target_date_str,
        })

    X = pd.DataFrame(rows_x)
    y = pd.Series(rows_y, name="target")
    meta = pd.DataFrame(rows_meta)
    return X, y, meta
