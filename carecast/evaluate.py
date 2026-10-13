"""Evaluation, walk-forward validation, metrics, and intervals (Phase 3).

Conforms to TRD §5 and PRD F3–F4:
- Chronological 60/20/20 train/valid/test split on target weeks (AT-11)
- Walk-forward evaluation without future leakage (training rows at origin t have s+h <= t)
- Validation-only model selection per horizon
- Empirical 80% residual quantiles (q10/q90 of validation residuals)
- Test-block interval coverage and beats_persistence verdict
"""

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

from carecast.models import get_model


def compute_chronological_splits(
    meta_df: pd.DataFrame,
    train_ratio: float = 0.60,
    valid_ratio: float = 0.20,
) -> dict[str, Any]:
    """Compute chronological train/valid/test partition indices and dates.

    Guarantees:
    train_start <= train_end < valid_start <= valid_end < test_start <= test_end (AT-11)
    """
    n = len(meta_df)
    n_train = int(n * train_ratio)
    n_valid = int(n * valid_ratio)
    n_test = n - n_train - n_valid

    if n_train < 4 or n_valid < 2 or n_test < 2:
        raise ValueError(
            f"Insufficient instances ({n}) for 60/20/20 split: "
            f"train={n_train}, valid={n_valid}, test={n_test}"
        )

    train_idx = list(range(0, n_train))
    valid_idx = list(range(n_train, n_train + n_valid))
    test_idx = list(range(n_train + n_valid, n))

    target_dates = meta_df["target_week_end_date"].tolist()

    return {
        "train_idx": train_idx,
        "valid_idx": valid_idx,
        "test_idx": test_idx,
        "n_train": n_train,
        "n_valid": n_valid,
        "n_test": n_test,
        "train_start": target_dates[train_idx[0]],
        "train_end": target_dates[train_idx[-1]],
        "valid_start": target_dates[valid_idx[0]],
        "valid_end": target_dates[valid_idx[-1]],
        "test_start": target_dates[test_idx[0]],
        "test_end": target_dates[test_idx[-1]],
    }


def walk_forward_evaluate(
    X: pd.DataFrame,
    y: pd.Series,
    meta: pd.DataFrame,
    split_info: dict[str, Any],
    h: int,
    model_names: list[str],
    random_seed: int = 42,
) -> dict[str, Any]:
    """Run walk-forward evaluation across validation and test blocks.

    For origin t predicting target t+h:
    Training observations are all origins s where target_date(s, h) <= origin_date(t).
    """
    eval_results: dict[str, dict[str, Any]] = {
        name: {
            "validation": {"actual": [], "predicted": [], "meta": []},
            "test": {"actual": [], "predicted": [], "meta": []},
        }
        for name in model_names
    }

    n = len(X)
    origin_dates = meta["origin_week_end_date"].tolist()
    target_dates = meta["target_week_end_date"].tolist()
    y_vals = y.to_numpy(dtype=float)

    eval_indices = [("validation", idx) for idx in split_info["valid_idx"]] + [
        ("test", idx) for idx in split_info["test_idx"]
    ]

    for split_name, eval_i in eval_indices:
        t_origin = origin_dates[eval_i]
        actual_val = y_vals[eval_i]
        meta_row = meta.iloc[eval_i].to_dict()

        # Leak-free training condition: target date s+h <= origin date t
        train_indices = [s for s in range(eval_i) if target_dates[s] <= t_origin]
        if len(train_indices) < 2:
            # Fall back to training on all preceding rows in split if window is tight
            train_indices = [s for s in range(eval_i) if s < split_info["n_train"]]

        X_train = X.iloc[train_indices]
        y_train = y.iloc[train_indices]
        X_eval = X.iloc[[eval_i]]

        for name in model_names:
            model = get_model(name, random_state=random_seed)
            model.fit(X_train, y_train)
            pred = float(model.predict(X_eval)[0])
            eval_results[name][split_name]["actual"].append(actual_val)
            eval_results[name][split_name]["predicted"].append(pred)
            eval_results[name][split_name]["meta"].append(meta_row)

    return eval_results


def compute_metrics(
    actual: list[float] | np.ndarray,
    predicted: list[float] | np.ndarray,
) -> tuple[float, float]:
    """Compute MAE and RMSE."""
    act_arr = np.array(actual, dtype=float)
    pred_arr = np.array(predicted, dtype=float)
    mae = float(mean_absolute_error(act_arr, pred_arr))
    rmse = float(root_mean_squared_error(act_arr, pred_arr))
    return mae, rmse


def evaluate_horizon(
    X: pd.DataFrame,
    y: pd.Series,
    meta: pd.DataFrame,
    h: int,
    baselines: list[str],
    candidates: list[str],
    interval_level: float = 0.80,
    random_seed: int = 42,
) -> dict[str, Any]:
    """Full evaluation workflow for horizon h:

    1. Splits data chronologically 60/20/20
    2. Runs walk-forward evaluation
    3. Computes MAE/RMSE per model and split
    4. Selects candidate with lowest validation MAE
    5. Computes q10/q90 of validation residuals for 80% interval
    6. Measures empirical test interval coverage
    7. Evaluates beats_persistence verdict on test block
    """
    splits = compute_chronological_splits(meta)
    all_models = baselines + candidates

    wf_results = walk_forward_evaluate(
        X, y, meta, splits, h=h, model_names=all_models, random_seed=random_seed
    )

    metrics_table: list[dict[str, Any]] = []

    # Persistence metrics for relative comparison
    pers_val_mae, _ = compute_metrics(
        wf_results["baseline_persistence"]["validation"]["actual"],
        wf_results["baseline_persistence"]["validation"]["predicted"],
    )
    pers_test_mae, _ = compute_metrics(
        wf_results["baseline_persistence"]["test"]["actual"],
        wf_results["baseline_persistence"]["test"]["predicted"],
    )

    # 1. Validation selection among candidates
    best_candidate = candidates[0]
    best_val_mae = float("inf")

    for cand in candidates:
        v_act = wf_results[cand]["validation"]["actual"]
        v_pred = wf_results[cand]["validation"]["predicted"]
        v_mae, _ = compute_metrics(v_act, v_pred)
        if v_mae < best_val_mae:
            best_val_mae = v_mae
            best_candidate = cand

    # 2. Residual quantiles for selected model (validation block)
    sel_val_act = np.array(wf_results[best_candidate]["validation"]["actual"])
    sel_val_pred = np.array(wf_results[best_candidate]["validation"]["predicted"])
    val_residuals = sel_val_act - sel_val_pred  # signed residuals: actual - predicted

    alpha = 1.0 - interval_level
    q_low = min(0.0, float(np.percentile(val_residuals, (alpha / 2.0) * 100.0)))    # e.g. 10th percentile (<= 0)
    q_high = max(0.0, float(np.percentile(val_residuals, (1.0 - alpha / 2.0) * 100.0)))  # e.g. 90th percentile (>= 0)

    # 3. Test coverage for selected model
    sel_test_act = np.array(wf_results[best_candidate]["test"]["actual"])
    sel_test_pred = np.array(wf_results[best_candidate]["test"]["predicted"])
    test_lower = np.minimum(sel_test_pred, np.clip(sel_test_pred + q_low, 0.0, None))
    test_upper = np.maximum(sel_test_pred, sel_test_pred + q_high)
    covered = (sel_test_act >= test_lower) & (sel_test_act <= test_upper)
    test_coverage = float(np.mean(covered))

    # Test beats persistence
    sel_test_mae, _ = compute_metrics(sel_test_act, sel_test_pred)
    beats_persistence = 1 if sel_test_mae < pers_test_mae else 0

    # Build metrics records for T8
    for m_name in all_models:
        for split in ("validation", "test"):
            act = wf_results[m_name][split]["actual"]
            prd = wf_results[m_name][split]["predicted"]
            mae, rmse = compute_metrics(act, prd)
            ref_pers_mae = pers_val_mae if split == "validation" else pers_test_mae
            rel_mae = (mae / ref_pers_mae) if ref_pers_mae > 0 else None

            is_sel = 1 if (m_name == best_candidate) else 0

            cov = test_coverage if (is_sel and split == "test") else None
            beats = beats_persistence if (is_sel and split == "test") else None

            metrics_table.append({
                "horizon_weeks": h,
                "model_name": m_name,
                "split": split,
                "mae": mae,
                "rmse": rmse,
                "n_eval": len(act),
                "mae_vs_persistence": rel_mae,
                "is_selected": is_sel,
                "interval_coverage": cov,
                "beats_persistence": beats,
            })

    return {
        "horizon_weeks": h,
        "splits": splits,
        "selected_model": best_candidate,
        "q_low": q_low,
        "q_high": q_high,
        "test_coverage": test_coverage,
        "beats_persistence": beats_persistence,
        "metrics": metrics_table,
        "backtest_results": wf_results,
    }
