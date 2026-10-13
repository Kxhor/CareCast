"""Explainability module for CareCast forecasts (Phase 3).

Conforms to TRD §5.4 and PRD F6:
1. Linear additive contributions:
   contribution_j = coef_j * (x_j - mean_train_j)
   base = mean training prediction = intercept + sum(coef_j * mean_train_j)
   Guarantees: base + sum(contribution_j) == prediction (AT-18)
2. Permutation importance:
   Evaluated on the validation block with negative MAE scoring
3. Plain-language explanation templates:
   Uses "associated with" language only; never asserts causality (AT-19)
"""

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

from carecast.models import LinearLagModel


# Plain-language labels for feature names
FEATURE_LABELS: dict[str, str] = {
    "y_lag0": "most recent admissions (current week)",
    "y_lag1": "admissions from 1 week ago",
    "y_lag2": "admissions from 2 weeks ago",
    "y_lag3": "admissions from 3 weeks ago",
    "roll_mean_4": "4-week average admission level",
    "woy_sin": "seasonal timing (sine cycle)",
    "woy_cos": "seasonal timing (cosine cycle)",
    "seasonal_lag52": "admissions from 52 weeks prior",
    "pct_reporting": "hospital reporting coverage rate",
}


def compute_linear_contributions(
    model: LinearLagModel,
    feature_vector: pd.Series | dict[str, Any],
) -> tuple[float, list[dict[str, Any]]]:
    """Compute exact additive feature contributions for a LinearLagModel.

    Guarantees: base + sum(contributions) == raw_prediction (|Δ| < 1e-9).
    """
    if not isinstance(model, LinearLagModel):
        raise TypeError("Linear contributions are only defined for LinearLagModel.")

    reg = model.regressor
    intercept = float(reg.intercept_)
    feature_names = model.feature_names_
    coefs = reg.coef_

    # Base is prediction evaluated at training feature means
    base = intercept + float(sum(coef * model.feature_means_[feat] for coef, feat in zip(coefs, feature_names)))

    contributions: list[dict[str, Any]] = []

    for coef, feat in zip(coefs, feature_names):
        x_val = float(feature_vector[feat])
        x_mean = float(model.feature_means_[feat])
        contrib = float(coef * (x_val - x_mean))
        contributions.append({
            "feature_name": feat,
            "value": contrib,
            "feature_value": x_val,
        })

    return base, contributions


def compute_permutation_importance(
    model: Any,
    X_val: pd.DataFrame,
    y_val: pd.Series | np.ndarray,
    n_repeats: int = 10,
    random_seed: int = 42,
) -> list[dict[str, Any]]:
    """Compute permutation importance on the validation set using negative MAE."""
    perm = permutation_importance(
        model.regressor,
        X_val,
        y_val,
        scoring="neg_mean_absolute_error",
        n_repeats=n_repeats,
        random_state=random_seed,
    )

    importances: list[dict[str, Any]] = []
    feature_names = list(X_val.columns)

    for idx, feat in enumerate(feature_names):
        mean_imp = float(perm.importances_mean[idx])
        importances.append({
            "feature_name": feat,
            "value": mean_imp,
            "feature_value": None,
        })

    # Sort descending by importance
    importances.sort(key=lambda item: item["value"], reverse=True)
    return importances


def generate_plain_language_text(
    contributions: list[dict[str, Any]],
    horizon_weeks: int,
) -> str:
    """Generate plain-language explanation text from stored numbers.

    Strictly adheres to AT-19: uses 'associated with' language only.
    Contains zero causal verbs (caused, leads to, because, due to, resulted in).
    """
    if not contributions:
        return f"For the {horizon_weeks}-week forecast, model features are balanced."

    # Filter out __base__ if present
    feature_contribs = [c for c in contributions if c["feature_name"] != "__base__"]
    if not feature_contribs:
        return f"For the {horizon_weeks}-week forecast, baseline prediction represents historical mean level."

    # Sort by absolute contribution value
    sorted_contribs = sorted(feature_contribs, key=lambda c: abs(c["value"]), reverse=True)
    top = sorted_contribs[0]

    label = FEATURE_LABELS.get(top["feature_name"], top["feature_name"])
    direction = "positive" if top["value"] >= 0 else "negative"
    val_str = f"{top['value']:+.1f}"

    text = (
        f"For the {horizon_weeks}-week forecast, {label} is associated with "
        f"the largest {direction} statistical contribution ({val_str} admissions relative to historical mean)."
    )
    return text
