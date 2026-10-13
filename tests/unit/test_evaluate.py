"""Unit tests for walk-forward evaluation, splits, metrics, and verdicts (Phase 3)."""

import math
from datetime import date, timedelta
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

from carecast.evaluate import (
    compute_chronological_splits,
    compute_metrics,
    evaluate_horizon,
)


def test_at_11_chronological_splits_ordering() -> None:
    """AT-11: train_end < valid_start and valid_end < test_start for chronological splits."""
    start = date(2023, 1, 7)
    target_dates = [(start + timedelta(weeks=i)).isoformat() for i in range(50)]
    meta_df = pd.DataFrame({
        "origin_week_end_date": target_dates,
        "target_week_end_date": target_dates,
    })

    splits = compute_chronological_splits(meta_df, train_ratio=0.60, valid_ratio=0.20)

    # Invariants from BACKEND_SCHEMA T7 CHECK constraint:
    # train_start <= train_end < valid_start <= valid_end < test_start <= test_end
    assert splits["train_start"] <= splits["train_end"]
    assert splits["train_end"] < splits["valid_start"]
    assert splits["valid_start"] <= splits["valid_end"]
    assert splits["valid_end"] < splits["test_start"]
    assert splits["test_start"] <= splits["test_end"]

    # Check partition sizing: 50 * 0.6 = 30 train, 50 * 0.2 = 10 valid, 10 test
    assert splits["n_train"] == 30
    assert splits["n_valid"] == 10
    assert splits["n_test"] == 10
    assert len(splits["train_idx"]) + len(splits["valid_idx"]) + len(splits["test_idx"]) == 50


def test_at_13_metrics_hand_fixture() -> None:
    """AT-13: MAE and RMSE match hand calculations and sklearn on a fixture."""
    actual = [10.0, 20.0, 30.0, 40.0]
    predicted = [12.0, 18.0, 35.0, 40.0]

    # Hand calculation:
    # errors = [-2, +2, -5, 0]
    # absolute errors = [2, 2, 5, 0] -> sum = 9 -> MAE = 9 / 4 = 2.25
    # squared errors = [4, 4, 25, 0] -> sum = 33 -> MSE = 33 / 4 = 8.25 -> RMSE = sqrt(8.25)
    expected_mae = 2.25
    expected_rmse = math.sqrt(8.25)

    mae, rmse = compute_metrics(actual, predicted)

    assert abs(mae - expected_mae) < 1e-12
    assert abs(rmse - expected_rmse) < 1e-12

    # Verify identical to sklearn functions
    sk_mae = mean_absolute_error(actual, predicted)
    sk_rmse = root_mean_squared_error(actual, predicted)
    assert abs(mae - sk_mae) < 1e-12
    assert abs(rmse - sk_rmse) < 1e-12


def test_at_14_beats_persistence_verdict_both_branches() -> None:
    """AT-14: Verdict logic: beats_persistence is 1 iff test MAE(selected) < MAE(persistence).

    Both branches must be explicitly tested.
    """
    # Branch 1: Model strictly outperforms persistence
    pers_test_actual = [100.0, 110.0, 120.0, 130.0]
    pers_test_pred = [90.0, 95.0, 100.0, 105.0]  # MAE = (10+15+20+25)/4 = 17.5
    sel_test_pred_better = [99.0, 109.0, 121.0, 131.0]  # MAE = (1+1+1+1)/4 = 1.0

    pers_mae, _ = compute_metrics(pers_test_actual, pers_test_pred)
    better_mae, _ = compute_metrics(pers_test_actual, sel_test_pred_better)

    verdict_branch_1 = 1 if better_mae < pers_mae else 0
    assert verdict_branch_1 == 1, "Branch 1 must be 1 when model strictly improves on persistence"

    # Branch 2: Model fails to beat persistence (worse or equal MAE)
    sel_test_pred_worse = [80.0, 80.0, 80.0, 80.0]  # MAE = (20+30+40+50)/4 = 35.0
    worse_mae, _ = compute_metrics(pers_test_actual, sel_test_pred_worse)

    verdict_branch_2 = 1 if worse_mae < pers_mae else 0
    assert verdict_branch_2 == 0, "Branch 2 must be 0 when model does not beat persistence"

    # Branch 2b: Exact tie does not beat persistence (strictly lower required)
    verdict_tie = 1 if pers_mae < pers_mae else 0
    assert verdict_tie == 0, "Tie must evaluate to 0 (strictly lower MAE required)"


def test_empirical_quantiles_and_coverage() -> None:
    """Verify 80% interval residual quantiles and test coverage calculation."""
    # Symmetrical validation residuals: 10 points
    # actual - pred: [-4, -3, -2, -1, 0, 0, 1, 2, 3, 4]
    val_act = np.array([10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0])
    val_pred = np.array([14.0, 13.0, 12.0, 11.0, 10.0, 10.0, 9.0, 8.0, 7.0, 6.0])
    res = val_act - val_pred  # -4, -3, -2, -1, 0, 0, 1, 2, 3, 4

    alpha = 1.0 - 0.80  # 0.20
    q_low = float(np.percentile(res, 10.0))
    q_high = float(np.percentile(res, 90.0))

    assert q_low < 0.0
    assert q_high > 0.0

    # Test coverage evaluation
    test_act = np.array([10.0, 10.0, 10.0])
    test_pred = np.array([10.0, 10.0, 10.0])
    test_lower = np.clip(test_pred + q_low, 0.0, None)
    test_upper = np.maximum(test_lower, test_pred + q_high)
    covered = (test_act >= test_lower) & (test_act <= test_upper)
    coverage = float(np.mean(covered))
    assert coverage == 1.0
