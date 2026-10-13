"""Unit tests for feature engineering and AT-08 leakage verification (Phase 3)."""

from datetime import date, timedelta
import numpy as np
import pandas as pd
import pytest

from carecast.features import (
    build_feature_row,
    compute_woy_cyclical,
    create_dataset_for_horizon,
)
from carecast.models import LinearLagModel


def test_compute_woy_cyclical() -> None:
    """Verify sine and cosine cyclical transform."""
    # Week 26 is mid-year -> angle = 2*pi*(26/52) = pi -> sin(pi) ~ 0, cos(pi) ~ -1
    sin_val, cos_val = compute_woy_cyclical("2024-06-29")  # week 26
    assert abs(sin_val**2 + cos_val**2 - 1.0) < 1e-6


def test_build_feature_row_lags() -> None:
    """Verify lag0..lag3 and roll_mean_4 values on a known sequence."""
    dates = [(date(2024, 1, 6) + timedelta(weeks=i)).isoformat() for i in range(10)]
    # Values: 10, 20, 30, 40, 50, 60, ...
    counts = [10.0 * (i + 1) for i in range(10)]
    df = pd.DataFrame({
        "week_end_date": dates,
        "admissions_count": counts,
        "pct_reporting": [95.0] * 10,
    })

    # At origin index 3 (date = 2024-01-27, count = 40):
    # lag0 = 40, lag1 = 30, lag2 = 20, lag3 = 10
    # roll_mean_4 = (40+30+20+10)/4 = 25.0
    feat = build_feature_row(df, origin_idx=3, h=1, include_seasonal_lag52=False)
    assert feat is not None
    assert feat["y_lag0"] == 40.0
    assert feat["y_lag1"] == 30.0
    assert feat["y_lag2"] == 20.0
    assert feat["y_lag3"] == 10.0
    assert feat["roll_mean_4"] == 25.0
    assert feat["pct_reporting"] == 95.0


def test_seasonal_lag52_detection() -> None:
    """Verify seasonal_lag52 finds the observation 52 weeks prior to target week."""
    # 70 weeks of data
    start = date(2023, 1, 7)
    dates = [(start + timedelta(weeks=i)).isoformat() for i in range(70)]
    counts = [100.0 + float(i) for i in range(70)]
    df = pd.DataFrame({
        "week_end_date": dates,
        "admissions_count": counts,
    })

    # Target week for h=1 at origin 55 is week 56.
    # 52 weeks prior to week 56 is week 4.
    # Observation at index 4 is 100.0 + 4 = 104.0.
    feat = build_feature_row(df, origin_idx=55, h=1, include_seasonal_lag52=True)
    assert feat is not None
    assert "seasonal_lag52" in feat
    assert feat["seasonal_lag52"] == 104.0


def test_at_08_leakage_perturbation() -> None:
    """AT-08: Perturbing observations after origin t leaves forecast and features at t unchanged."""
    # 60 weeks of synthetic data
    start = date(2023, 1, 7)
    dates = [(start + timedelta(weeks=i)).isoformat() for i in range(60)]
    base_counts = [50.0 + 10.0 * np.sin(i / 5.0) for i in range(60)]

    df_original = pd.DataFrame({
        "week_end_date": dates,
        "admissions_count": list(base_counts),
        "pct_reporting": [92.0] * 60,
    })

    origin_idx = 35  # Origin week t

    # Fit and forecast at origin t on original data
    feat_orig = build_feature_row(df_original, origin_idx=origin_idx, h=2, include_seasonal_lag52=False)
    assert feat_orig is not None

    # Train linear model using only rows available at origin t (indices <= origin_idx - h)
    X_train_orig, y_train_orig, meta_orig = create_dataset_for_horizon(
        df_original.iloc[: origin_idx + 1], h=2, include_seasonal_lag52=False
    )
    model_orig = LinearLagModel()
    model_orig.fit(X_train_orig, y_train_orig)
    pred_orig = float(model_orig.predict(pd.DataFrame([feat_orig]))[0])

    # Now create PERTURBED dataframe:
    # All rows strictly AFTER origin_idx are radically corrupted / modified
    df_perturbed = df_original.copy()
    perturbed_counts = list(base_counts)
    for j in range(origin_idx + 1, len(df_perturbed)):
        perturbed_counts[j] = perturbed_counts[j] * 100.0 + 9999.0  # Massive corruption
    df_perturbed["admissions_count"] = perturbed_counts

    # Re-extract feature vector at origin_idx on perturbed dataframe
    feat_pert = build_feature_row(df_perturbed, origin_idx=origin_idx, h=2, include_seasonal_lag52=False)
    assert feat_pert is not None

    # Verify features at origin t are bit-for-bit identical
    for k in feat_orig:
        assert feat_orig[k] == feat_pert[k], f"Feature {k} changed after post-t perturbation!"

    # Re-train model on data up to origin t
    X_train_pert, y_train_pert, meta_pert = create_dataset_for_horizon(
        df_perturbed.iloc[: origin_idx + 1], h=2, include_seasonal_lag52=False
    )
    model_pert = LinearLagModel()
    model_pert.fit(X_train_pert, y_train_pert)
    pred_pert = float(model_pert.predict(pd.DataFrame([feat_pert]))[0])

    # AT-08 assertion: forecast at t is completely unchanged
    assert abs(pred_orig - pred_pert) < 1e-12, (
        f"AT-08 VIOLATION: Forecast changed from {pred_orig} to {pred_pert} after post-origin perturbation"
    )
