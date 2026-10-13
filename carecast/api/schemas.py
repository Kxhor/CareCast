"""Pydantic request and response schemas for CareCast API v1 (Phase 4).

Strictly adheres to BACKEND_SCHEMA §7 & §8.
All models have extra='forbid' to reject unknown parameters.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Error Envelope (§7.1)
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    fields: list[str] = Field(default_factory=list)
    request_id: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error: ErrorDetail


# ---------------------------------------------------------------------------
# E1: Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    db_ok: bool
    data_as_of: str
    version: str


# ---------------------------------------------------------------------------
# E2: Meta
# ---------------------------------------------------------------------------

class AppMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    version: str
    env: str


class SourceMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    publisher: str
    dataset_id: str
    url: str
    retrieved_at: str
    file_sha256: str


class DiseaseMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    label: str
    available: bool
    reason: str | None = None


class JurisdictionMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    name: str
    level: str


class ScenarioDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min: float
    max: float
    presets: list[float]


class CapacityDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")
    typical_weekly_admissions: float
    alos_days: float
    staffed_beds: float
    patients_per_nurse: float
    is_simulated: bool
    note: str


class DefaultsMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    threshold_method: str
    interval_level: float
    scenario: ScenarioDefaults
    capacity: CapacityDefaults


class LimitationMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    text: str


class QualityIssueMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    check_name: str
    severity: str
    detail: str


class MetaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    app: AppMeta
    data_as_of: str
    source: SourceMeta
    diseases: list[DiseaseMeta]
    jurisdictions: list[JurisdictionMeta]
    horizons: list[int]
    target_kind: dict[str, str]
    defaults: DefaultsMeta
    limitations: list[LimitationMeta]
    quality_issues: list[QualityIssueMeta]
    disclaimer: str


# ---------------------------------------------------------------------------
# Shared Blocks (Summary, Forecast, Scenario)
# ---------------------------------------------------------------------------

class ThresholdInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: float
    source: str  # "default" | "override"


class ForecastThresholdInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: float
    source: str  # "default" | "override"
    method: str


class ActionsBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tier: str
    items: list[str]
    footer: str


# ---------------------------------------------------------------------------
# E3: Summary
# ---------------------------------------------------------------------------

class LatestObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    week_end_date: str
    value: float
    change_pct_vs_prior_week: float | None = None


class NextWeekForecast(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_week_end_date: str
    point: float
    lower: float
    upper: float
    tier: str
    model_name: str


class RingGauge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    forecast_pct_of_threshold: float | None = None
    lower_pct: float | None = None
    upper_pct: float | None = None


class RecentPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    week_end_date: str
    value: float


class SelectedSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    disease: str
    jurisdiction: str
    target_kind: str
    unit: str
    latest: LatestObservation
    threshold: ThresholdInfo
    next_week: NextWeekForecast
    ring: RingGauge
    recent: list[RecentPoint]
    actions: ActionsBlock


class WatchlistItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    disease: str
    label: str
    available: bool
    latest_value: float | None = None
    next_week_point: float | None = None
    tier: str | None = None
    threshold: float | None = None


class EvaluationHeadline(BaseModel):
    model_config = ConfigDict(extra="forbid")
    horizon_weeks: int
    selected_model: str
    test_mae: float
    persistence_test_mae: float
    beats_persistence: bool
    test_interval_coverage: float


class SummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data_as_of: str
    stale: bool
    selected: SelectedSummary
    watchlist: list[WatchlistItem]
    evaluation_headline: EvaluationHeadline


# ---------------------------------------------------------------------------
# E4: Observations
# ---------------------------------------------------------------------------

class ObservationPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    week_end_date: str
    value: float
    is_imputed: bool
    pct_reporting: float | None = None


class ObservationsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    disease: str
    jurisdiction: str
    target_kind: str
    unit: str
    count: int
    points: list[ObservationPoint]


# ---------------------------------------------------------------------------
# E5: Forecast
# ---------------------------------------------------------------------------

class RunMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    created_at: str
    data_end_date: str
    target_kind: str


class ForecastHorizonItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    horizon_weeks: int
    origin_week_end_date: str
    target_week_end_date: str
    point: float
    lower: float
    upper: float
    model_name: str
    tier: str


class ForecastResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run: RunMeta
    interval_level: float
    threshold: ForecastThresholdInfo
    horizons: list[ForecastHorizonItem]
    actions: ActionsBlock
    disclaimer: str


# ---------------------------------------------------------------------------
# E6: Evaluation
# ---------------------------------------------------------------------------

class RunSplits(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    train: list[str]
    validation: list[str]
    test: list[str]
    n_train: int
    n_valid: int
    n_test: int


class MetricItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    horizon_weeks: int
    model_name: str
    split: str
    mae: float
    rmse: float
    n_eval: int
    mae_vs_persistence: float | None = None
    is_selected: bool


class SelectedModelItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    horizon_weeks: int
    model_name: str
    beats_persistence: bool
    test_interval_coverage: float


class VerdictItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    horizon_weeks: int
    beats_persistence: bool
    text: str


class BacktestPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_week_end_date: str
    actual: float
    predicted_selected: float
    predicted_persistence: float


class BacktestSeries(BaseModel):
    model_config = ConfigDict(extra="forbid")
    horizon_weeks: int
    points: list[BacktestPoint]


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run: RunSplits
    metrics: list[MetricItem]
    selected: list[SelectedModelItem]
    verdicts: list[VerdictItem]
    backtest: BacktestSeries


# ---------------------------------------------------------------------------
# E7: Explain
# ---------------------------------------------------------------------------

class FeatureContributionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature: str
    label: str
    value: float
    feature_value: float | None = None


class PermutationImportanceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature: str
    label: str
    value: float


class ExplainResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    horizon_weeks: int
    model_name: str
    base_value: float
    prediction: float
    contributions: list[FeatureContributionItem] | None = None
    permutation_importance: list[PermutationImportanceItem]
    text: str
    note: str


# ---------------------------------------------------------------------------
# E8: Scenario
# ---------------------------------------------------------------------------

class CapacityInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    typical_weekly_admissions: float = Field(..., gt=0, le=1_000_000)
    alos_days: float = Field(..., ge=0.5, le=60)
    staffed_beds: float = Field(..., gt=0, le=100_000)
    patients_per_nurse: float = Field(..., ge=1, le=50)


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    disease: str = "flu"
    jurisdiction: str = "US"
    surge_pct: float = Field(..., ge=-50, le=100)
    threshold: float | None = Field(default=None, ge=0, le=1e9)
    capacity: CapacityInputs | None = None


class HorizonBand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    point: float
    lower: float
    upper: float
    tier: str


class ScenarioHorizonItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    horizon_weeks: int
    target_week_end_date: str
    base: HorizonBand
    scenario: HorizonBand


class CapacityHorizonItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    horizon_weeks: int
    relative_change: float | None = None
    hospital_weekly_admissions: float | None = None
    est_occupied_beds: float | None = None
    bed_gap: float | None = None
    nurses_per_shift: float | None = None


class CapacityBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_simulated: bool
    label: str
    reference_level: float
    inputs: CapacityInputs
    horizons: list[CapacityHorizonItem]
    formulae: list[str]
    message: str | None = None


class ScenarioResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_scenario: bool
    label: str
    surge_pct: float
    threshold: ThresholdInfo
    horizons: list[ScenarioHorizonItem]
    capacity: CapacityBlock
    actions: ActionsBlock
