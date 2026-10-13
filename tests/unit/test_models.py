"""Unit tests for forecasting models and AT-12 baseline predictions (Phase 3)."""

import numpy as np
import pandas as pd
import pytest

from carecast.models import (
    HgbLagModel,
    LinearLagModel,
    PersistenceBaseline,
    SeasonalNaiveBaseline,
    get_model,
)


def test_at_12_persistence_hand_fixture() -> None:
    """AT-12: Persistence baseline matches hand-calculated value on a fixture."""
    # Fixture with y_lag0 = 120.0
    X = pd.DataFrame([
        {"y_lag0": 120.0, "y_lag1": 110.0, "y_lag2": 105.0, "y_lag3": 100.0},
        {"y_lag0": 145.5, "y_lag1": 120.0, "y_lag2": 110.0, "y_lag3": 105.0},
    ])
    baseline = PersistenceBaseline()
    baseline.fit(X, y=np.array([125.0, 150.0]))
    preds = baseline.predict(X)

    # Hand-calculated expectation: exact copy of y_lag0
    assert preds[0] == 120.0
    assert preds[1] == 145.5


def test_at_12_seasonal_naive_hand_fixture() -> None:
    """AT-12: Seasonal naive baseline matches hand-calculated value on a fixture."""
    # Fixture with seasonal_lag52 = 88.0
    X = pd.DataFrame([
        {"y_lag0": 120.0, "seasonal_lag52": 88.0},
        {"y_lag0": 145.0, "seasonal_lag52": 92.5},
    ])
    baseline = SeasonalNaiveBaseline()
    baseline.fit(X, y=np.array([125.0, 150.0]))
    preds = baseline.predict(X)

    # Hand-calculated expectation: exact copy of seasonal_lag52
    assert preds[0] == 88.0
    assert preds[1] == 92.5


def test_linear_lag_negative_clipping() -> None:
    """Verify negative predictions are clipped to 0.0 in LinearLagModel."""
    X_train = pd.DataFrame({
        "y_lag0": [10.0, 20.0, 30.0],
        "roll_mean_4": [10.0, 20.0, 30.0],
    })
    y_train = np.array([5.0, 15.0, 25.0])

    model = LinearLagModel()
    model.fit(X_train, y_train)

    # Test feature vector with zero/negative inputs that would yield negative linear prediction
    X_test = pd.DataFrame({
        "y_lag0": [-100.0],
        "roll_mean_4": [-100.0],
    })
    preds = model.predict(X_test)
    assert preds[0] == 0.0  # Clipped to 0.0, never negative


def test_hgb_lag_deterministic_and_clipping() -> None:
    """Verify HistGradientBoostingRegressor is reproducible and clips to 0."""
    X_train = pd.DataFrame({
        "y_lag0": [10.0, 20.0, 30.0, 40.0, 50.0] * 5,
        "roll_mean_4": [10.0, 20.0, 30.0, 40.0, 50.0] * 5,
    })
    y_train = np.array([12.0, 22.0, 32.0, 42.0, 52.0] * 5)

    m1 = HgbLagModel(random_state=42).fit(X_train, y_train)
    m2 = HgbLagModel(random_state=42).fit(X_train, y_train)

    preds1 = m1.predict(X_train)
    preds2 = m2.predict(X_train)
    assert np.all(preds1 == preds2)
    assert np.all(preds1 >= 0.0)


def test_get_model_factory() -> None:
    """Verify model factory raises on invalid name."""
    with pytest.raises(ValueError):
        get_model("xgboost_model")
