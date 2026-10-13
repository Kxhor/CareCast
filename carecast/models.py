"""Forecasting models and baselines (Phase 3).

Four models per TRD §5.3:
1. baseline_persistence: ŷ_{t+h} = y_t (predicts y_lag0)
2. baseline_seasonal_naive: ŷ_{t+h} = y_{t+h-52} (predicts seasonal_lag52 when available)
3. linear_lag: LinearRegression on lag features
4. hgb_lag: HistGradientBoostingRegressor with fixed random_state

All models clip negative predictions to 0 and record clipping occurrences.
No model serialization via pickle/joblib is used (models fit on demand in pipeline).
"""

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import HistGradientBoostingRegressor


class PersistenceBaseline:
    """Persistence baseline: predicts most recent observed value at origin t (y_lag0)."""

    def __init__(self) -> None:
        self.name = "baseline_persistence"
        self.is_fitted = True

    def fit(self, X: pd.DataFrame, y: pd.Series | np.ndarray) -> PersistenceBaseline:
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if "y_lag0" not in X.columns:
            raise KeyError("y_lag0 feature required for persistence baseline.")
        preds = X["y_lag0"].to_numpy(dtype=float)
        return np.clip(preds, 0.0, None)


class SeasonalNaiveBaseline:
    """Seasonal-naive baseline: predicts value 52 weeks prior to target week (seasonal_lag52)."""

    def __init__(self) -> None:
        self.name = "baseline_seasonal_naive"
        self.is_fitted = True

    def fit(self, X: pd.DataFrame, y: pd.Series | np.ndarray) -> SeasonalNaiveBaseline:
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if "seasonal_lag52" not in X.columns:
            raise KeyError("seasonal_lag52 feature required for seasonal naive baseline.")
        preds = X["seasonal_lag52"].to_numpy(dtype=float)
        return np.clip(preds, 0.0, None)


class LinearLagModel:
    """Linear regression on lag/cyclical features."""

    def __init__(self) -> None:
        self.name = "linear_lag"
        self.regressor = LinearRegression()
        self.feature_names_: list[str] = []
        self.feature_means_: dict[str, float] = {}
        self.mean_prediction_: float = 0.0

    def fit(self, X: pd.DataFrame, y: pd.Series | np.ndarray) -> LinearLagModel:
        self.feature_names_ = list(X.columns)
        self.regressor.fit(X, y)
        for col in self.feature_names_:
            self.feature_means_[col] = float(X[col].mean())
        # Mean training prediction
        train_preds = self.regressor.predict(X)
        self.mean_prediction_ = float(np.mean(train_preds))
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        raw_preds = self.regressor.predict(X[self.feature_names_])
        return np.clip(raw_preds, 0.0, None)


class HgbLagModel:
    """HistGradientBoostingRegressor with fixed random seed."""

    def __init__(self, random_state: int = 42) -> None:
        self.name = "hgb_lag"
        self.random_state = random_state
        self.regressor = HistGradientBoostingRegressor(random_state=random_state)
        self.feature_names_: list[str] = []

    def fit(self, X: pd.DataFrame, y: pd.Series | np.ndarray) -> HgbLagModel:
        self.feature_names_ = list(X.columns)
        self.regressor.fit(X, y)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        raw_preds = self.regressor.predict(X[self.feature_names_])
        return np.clip(raw_preds, 0.0, None)


def get_model(name: str, random_state: int = 42) -> Any:
    """Factory function for model instances."""
    if name == "baseline_persistence":
        return PersistenceBaseline()
    elif name == "baseline_seasonal_naive":
        return SeasonalNaiveBaseline()
    elif name == "linear_lag":
        return LinearLagModel()
    elif name == "hgb_lag":
        return HgbLagModel(random_state=random_state)
    else:
        raise ValueError(f"Unknown model name: {name}")
