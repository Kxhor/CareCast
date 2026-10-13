"""Unit tests for explainability and AT-18 additive identity (Phase 3)."""

import re
import numpy as np
import pandas as pd
import pytest

from carecast.explain import (
    compute_linear_contributions,
    compute_permutation_importance,
    generate_plain_language_text,
)
from carecast.models import LinearLagModel


def test_at_18_additive_identity() -> None:
    """AT-18: base + sum(contributions) == raw_prediction within 1e-9."""
    # Create dataset with multiple feature scales
    np.random.seed(42)
    n = 60
    X = pd.DataFrame({
        "y_lag0": np.random.uniform(50.0, 200.0, n),
        "y_lag1": np.random.uniform(40.0, 190.0, n),
        "roll_mean_4": np.random.uniform(45.0, 195.0, n),
        "woy_sin": np.sin(np.linspace(0, 2 * np.pi, n)),
        "woy_cos": np.cos(np.linspace(0, 2 * np.pi, n)),
    })
    # y with known coefficients and noise
    y = (
        0.5 * X["y_lag0"]
        + 0.2 * X["y_lag1"]
        + 0.3 * X["roll_mean_4"]
        + 15.0 * X["woy_sin"]
        - 10.0 * X["woy_cos"]
        + 25.0
        + np.random.normal(0, 2, n)
    )

    model = LinearLagModel()
    model.fit(X, y)

    # Test across multiple distinct feature vectors
    test_vectors = [
        X.iloc[0],
        X.iloc[15],
        X.iloc[30],
        pd.Series({
            "y_lag0": 175.0,
            "y_lag1": 160.0,
            "roll_mean_4": 165.0,
            "woy_sin": 0.8,
            "woy_cos": -0.6,
        }),
    ]

    for vec in test_vectors:
        df_vec = pd.DataFrame([vec])
        raw_pred = float(model.regressor.predict(df_vec)[0])

        base, contribs = compute_linear_contributions(model, vec)

        contrib_sum = sum(c["value"] for c in contribs)
        total_reconstructed = base + contrib_sum

        delta = abs(total_reconstructed - raw_pred)
        assert delta < 1e-9, (
            f"AT-18 VIOLATION: base ({base}) + sum ({contrib_sum}) = {total_reconstructed} "
            f"!= raw_pred ({raw_pred}), delta = {delta} (exceeds 1e-9 threshold)"
        )


def test_permutation_importance_validation_block() -> None:
    """Verify permutation importance returns valid sorted list of features."""
    X = pd.DataFrame({
        "y_lag0": [10.0, 20.0, 30.0, 40.0, 50.0] * 4,
        "y_lag1": [8.0, 18.0, 28.0, 38.0, 48.0] * 4,
    })
    y = np.array([12.0, 22.0, 32.0, 42.0, 52.0] * 4)

    model = LinearLagModel()
    model.fit(X, y)

    imps = compute_permutation_importance(model, X, y, n_repeats=5, random_seed=42)
    assert len(imps) == 2
    assert imps[0]["feature_name"] in ("y_lag0", "y_lag1")
    # Must be sorted descending
    assert imps[0]["value"] >= imps[1]["value"]


def test_at_19_non_causal_language() -> None:
    """AT-19 / F6: Plain-language text uses 'associated with' and contains no causal verbs."""
    contribs = [
        {"feature_name": "__base__", "value": 120.0},
        {"feature_name": "y_lag0", "value": 35.5},
        {"feature_name": "roll_mean_4", "value": -10.2},
    ]

    text = generate_plain_language_text(contribs, horizon_weeks=2)

    # Must contain "associated with"
    assert "associated with" in text

    # Must NOT contain forbidden causal terms: cause, caused, causing, leads to, because, due to, resulted in
    forbidden_causal_terms = [
        r"\bcause\b",
        r"\bcaused\b",
        r"\bcausing\b",
        r"\bleads to\b",
        r"\bbecause\b",
        r"\bdue to\b",
        r"\bresulted in\b",
    ]
    for pattern in forbidden_causal_terms:
        match = re.search(pattern, text, re.IGNORECASE)
        assert match is None, f"Causal language detected ({pattern}) in text: {text}"
