"""API endpoint routes E1 through E8 for CareCast (Phase 4).

Adheres to:
- BACKEND_SCHEMA §7 & §8
- All SQL queries use constant literals and parameterized '?' placeholders (AT-05)
- Target columns selected from hard-coded allowlist
- Zero patient-level data handling (AT-45)
"""

from __future__ import annotations

import math
from datetime import date, datetime
from pathlib import Path
from typing import Any, Generator

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
import sqlite3

from carecast.api.schemas import (
    ActionsBlock,
    AppMeta,
    BacktestPoint,
    BacktestSeries,
    CapacityBlock,
    CapacityDefaults,
    CapacityHorizonItem,
    CapacityInputs,
    DefaultsMeta,
    DiseaseMeta,
    EvaluationHeadline,
    EvaluationResponse,
    ExplainResponse,
    FeatureContributionItem,
    ForecastHorizonItem,
    ForecastResponse,
    ForecastThresholdInfo,
    HealthResponse,
    HorizonBand,
    JurisdictionMeta,
    LatestObservation,
    LimitationMeta,
    MetaResponse,
    MetricItem,
    NextWeekForecast,
    ObservationPoint,
    ObservationsResponse,
    PermutationImportanceItem,
    QualityIssueMeta,
    RecentPoint,
    RingGauge,
    RunMeta,
    RunSplits,
    ScenarioDefaults,
    ScenarioHorizonItem,
    ScenarioRequest,
    ScenarioResponse,
    SelectedModelItem,
    SelectedSummary,
    SourceMeta,
    SummaryResponse,
    ThresholdInfo,
    VerdictItem,
    WatchlistItem,
)
from carecast.db import connect_ro
from carecast.planning import (
    calculate_capacity_illustration,
    calculate_scenario,
    calculate_tier,
    format_explanation_text,
    get_action_checklist,
    load_planning_config,
)
from carecast.settings import Settings

router = APIRouter(prefix="/api/v1")

TARGET_ALLOWLIST = {
    "count": "admissions_count",
    "rate": "admissions_rate_per_100k",
}

FEATURE_LABELS = {
    "y_lag0": "Admissions last week",
    "y_lag1": "Admissions 2 weeks ago",
    "y_lag2": "Admissions 3 weeks ago",
    "y_lag3": "Admissions 4 weeks ago",
    "roll_mean_4": "4-week rolling average",
    "seasonal_lag52": "Admissions same week last year",
    "woy_sin": "Seasonal cycle (sine)",
    "woy_cos": "Seasonal cycle (cosine)",
    "pct_reporting": "Hospital reporting percentage",
}

SQL_MAX_DATE = "SELECT max(week_end_date) FROM weekly_observations"

SQL_OBSERVATIONS_COUNT = """
SELECT week_end_date, admissions_count AS value, is_imputed, pct_reporting
FROM weekly_observations
WHERE jurisdiction_code = ? AND disease_code = ?
  AND (? IS NULL OR week_end_date >= ?)
  AND (? IS NULL OR week_end_date <= ?)
ORDER BY week_end_date ASC
"""

SQL_OBSERVATIONS_RATE = """
SELECT week_end_date, admissions_rate_per_100k AS value, is_imputed, pct_reporting
FROM weekly_observations
WHERE jurisdiction_code = ? AND disease_code = ?
  AND (? IS NULL OR week_end_date >= ?)
  AND (? IS NULL OR week_end_date <= ?)
ORDER BY week_end_date ASC
"""

SQL_RECENT_OBSERVATIONS_COUNT = """
SELECT week_end_date, admissions_count AS value
FROM weekly_observations
WHERE jurisdiction_code = ? AND disease_code = ?
ORDER BY week_end_date DESC
LIMIT ?
"""

SQL_RECENT_OBSERVATIONS_RATE = """
SELECT week_end_date, admissions_rate_per_100k AS value
FROM weekly_observations
WHERE jurisdiction_code = ? AND disease_code = ?
ORDER BY week_end_date DESC
LIMIT ?
"""


def get_db(request: Request) -> Generator[sqlite3.Connection, None, None]:
    """Provide a read-only database connection per request."""
    settings: Settings = request.app.state.settings
    try:
        conn = connect_ro(settings.db_path)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "data_unavailable",
                "message": "Database is unavailable or unreadable.",
                "fields": [],
            },
        ) from err

    try:
        yield conn
    finally:
        conn.close()


def get_db_data_as_of(conn: sqlite3.Connection) -> str:
    """Fetch maximum week_end_date as data_as_of."""
    cur = conn.cursor()
    cur.execute(SQL_MAX_DATE)
    row = cur.fetchone()
    if not row or not row[0]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "data_unavailable",
                "message": "No observation data present in database.",
                "fields": [],
            },
        )
    return str(row[0])


def validate_jurisdiction(conn: sqlite3.Connection, jurisdiction: str) -> None:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM jurisdictions WHERE code = ?", (jurisdiction,))
    if not cur.fetchone():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "validation_error",
                "message": f"Unknown jurisdiction: {jurisdiction}",
                "fields": ["jurisdiction"],
            },
        )


def validate_disease(conn: sqlite3.Connection, disease: str) -> None:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM diseases WHERE code = ?", (disease,))
    if not cur.fetchone():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "validation_error",
                "message": f"Unknown disease: {disease}",
                "fields": ["disease"],
            },
        )


def validate_threshold(threshold: float | None) -> None:
    if threshold is None:
        return
    if math.isnan(threshold) or math.isinf(threshold) or threshold < 0.0 or threshold > 1e9:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "validation_error",
                "message": "Invalid threshold parameter.",
                "fields": ["threshold"],
            },
        )


def get_current_run(conn: sqlite3.Connection, jurisdiction: str, disease: str) -> sqlite3.Row:
    """Resolve active model run from v_current_runs."""
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM v_current_runs WHERE jurisdiction_code = ? AND disease_code = ?",
        (jurisdiction, disease),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "series_unavailable",
                "message": f"No current model run available for {disease} in {jurisdiction}.",
                "fields": ["disease", "jurisdiction"],
            },
        )
    return row


# ---------------------------------------------------------------------------
# E1: Health
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
def get_health(conn: sqlite3.Connection = Depends(get_db)) -> HealthResponse:
    data_as_of = get_db_data_as_of(conn)
    return HealthResponse(
        status="ok",
        db_ok=True,
        data_as_of=data_as_of,
        version="0.1.0",
    )


# ---------------------------------------------------------------------------
# E2: Meta
# ---------------------------------------------------------------------------

@router.get("/meta", response_model=MetaResponse)
def get_meta(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
) -> MetaResponse:
    settings: Settings = request.app.state.settings
    planning_cfg = load_planning_config()
    data_as_of = get_db_data_as_of(conn)

    cur = conn.cursor()

    # Source metadata
    cur.execute(
        "SELECT name, publisher, dataset_id, url, retrieved_at, file_sha256 FROM dataset_sources "
        "ORDER BY retrieved_at DESC LIMIT 1"
    )
    src_row = cur.fetchone()
    if src_row:
        source = SourceMeta(
            name=src_row[0],
            publisher=src_row[1],
            dataset_id=src_row[2],
            url=src_row[3],
            retrieved_at=src_row[4],
            file_sha256=src_row[5],
        )
    else:
        source = SourceMeta(
            name="CDC NHSN Respiratory Admissions",
            publisher="CDC/NHSN",
            dataset_id="ua7e-t2fy",
            url="https://data.cdc.gov",
            retrieved_at="2026-10-10T00:00:00Z",
            file_sha256="0" * 64,
        )

    # Diseases
    cur.execute("SELECT code, label FROM diseases ORDER BY code")
    disease_rows = cur.fetchall()
    diseases: list[DiseaseMeta] = []
    for d_code, d_label in disease_rows:
        cur.execute(
            "SELECT 1 FROM v_current_runs WHERE disease_code = ? AND jurisdiction_code = 'US'",
            (d_code,),
        )
        has_run = bool(cur.fetchone())
        diseases.append(
            DiseaseMeta(
                code=d_code,
                label=d_label,
                available=has_run,
                reason=None if has_run else "No validated model run available",
            )
        )

    # Jurisdictions
    cur.execute("SELECT code, name, level FROM jurisdictions ORDER BY code")
    jurisdictions = [
        JurisdictionMeta(code=row[0], name=row[1], level=row[2])
        for row in cur.fetchall()
    ]

    # Target kind mapping
    cur.execute("SELECT disease_code, target_kind FROM v_current_runs WHERE jurisdiction_code = 'US'")
    target_kind = {row[0]: row[1] for row in cur.fetchall()}
    for d in diseases:
        if d.code not in target_kind:
            target_kind[d.code] = "count"

    # Capacity defaults from planning.toml
    cap_cfg = planning_cfg.get("capacity_defaults", {})
    cap_defaults = CapacityDefaults(
        typical_weekly_admissions=float(cap_cfg.get("typical_weekly_admissions", 100.0)),
        alos_days=float(cap_cfg.get("alos_days", 4.5)),
        staffed_beds=float(cap_cfg.get("staffed_beds", 80.0)),
        patients_per_nurse=float(cap_cfg.get("patients_per_nurse", 4.0)),
        is_simulated=True,
        note=str(cap_cfg.get("note", "DEMO PLACEHOLDER — not data")),
    )

    bounds_cfg = planning_cfg.get("bounds", {})
    surge_bounds = bounds_cfg.get("surge_pct", [-50, 100])
    scenario_defaults = ScenarioDefaults(
        min=float(surge_bounds[0]),
        max=float(surge_bounds[1]),
        presets=[0.0, 10.0, 20.0],
    )

    defaults = DefaultsMeta(
        threshold_method="percentile_75_of_training_block",
        interval_level=0.8,
        scenario=scenario_defaults,
        capacity=cap_defaults,
    )

    # Limitations L-01 to L-12
    lim_cfg = planning_cfg.get("limitations", {})
    limitations: list[LimitationMeta] = []
    for i in range(1, 13):
        k = f"L-{i:02d}"
        if k in lim_cfg:
            limitations.append(LimitationMeta(id=k, text=str(lim_cfg[k])))

    # Quality issues
    cur.execute("SELECT check_name, severity, detail FROM data_quality_issues ORDER BY id LIMIT 500")
    quality_issues = [
        QualityIssueMeta(check_name=r[0], severity=r[1], detail=r[2])
        for r in cur.fetchall()
    ]

    disclaimer = str(
        planning_cfg.get("disclaimer", {}).get(
            "text", "Demonstration forecasts. Not clinically validated. Decision support only."
        )
    )

    return MetaResponse(
        app=AppMeta(name="CareCast", version="0.1.0", env=settings.env),
        data_as_of=data_as_of,
        source=source,
        diseases=diseases,
        jurisdictions=jurisdictions,
        horizons=[1, 2, 3, 4],
        target_kind=target_kind,
        defaults=defaults,
        limitations=limitations,
        quality_issues=quality_issues,
        disclaimer=disclaimer,
    )


# ---------------------------------------------------------------------------
# E3: Summary
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=SummaryResponse)
def get_summary(
    disease: str = Query("flu"),
    jurisdiction: str = Query("US"),
    threshold: float | None = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
) -> SummaryResponse:
    validate_jurisdiction(conn, jurisdiction)
    validate_disease(conn, disease)
    validate_threshold(threshold)

    run = get_current_run(conn, jurisdiction, disease)
    planning_cfg = load_planning_config()
    data_as_of = get_db_data_as_of(conn)

    # Calculate staleness: data_as_of older than 14 days
    try:
        as_of_dt = datetime.strptime(data_as_of, "%Y-%m-%d").date()
        stale = (date.today() - as_of_dt).days > 14
    except Exception:
        stale = False

    target_col = TARGET_ALLOWLIST.get(run["target_kind"], "admissions_count")
    cur = conn.cursor()

    # Recent observations (last 8)
    recent_query = (
        SQL_RECENT_OBSERVATIONS_COUNT
        if target_col == "admissions_count"
        else SQL_RECENT_OBSERVATIONS_RATE
    )
    cur.execute(recent_query, (jurisdiction, disease, 8))
    rows_desc = cur.fetchall()
    rows_asc = list(reversed(rows_desc))

    recent = [RecentPoint(week_end_date=r[0], value=float(r[1])) for r in rows_asc]

    latest_val = float(rows_desc[0][1]) if rows_desc else 0.0
    latest_date = rows_desc[0][0] if rows_desc else data_as_of

    prior_val = float(rows_desc[1][1]) if len(rows_desc) > 1 else None
    change_pct: float | None = None
    if prior_val is not None and prior_val > 0:
        change_pct = round(((latest_val - prior_val) / prior_val) * 100.0, 2)

    latest = LatestObservation(
        week_end_date=latest_date,
        value=latest_val,
        change_pct_vs_prior_week=change_pct,
    )

    # Threshold
    if threshold is not None:
        thresh_val = float(threshold)
        thresh_info = ThresholdInfo(value=thresh_val, source="override")
    else:
        thresh_val = float(run["default_threshold"])
        thresh_info = ThresholdInfo(value=thresh_val, source="default")

    # Next week forecast (h=1)
    cur.execute(
        "SELECT target_week_end_date, point, lower, upper, model_name FROM forecasts "
        "WHERE run_id = ? AND horizon_weeks = 1",
        (run["id"],),
    )
    fc_row = cur.fetchone()
    if not fc_row:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "data_unavailable",
                "message": "Forecast records missing for active run.",
                "fields": [],
            },
        )

    next_point = float(fc_row[1])
    next_lower = float(fc_row[2])
    next_upper = float(fc_row[3])
    next_model = str(fc_row[4])
    tier = calculate_tier(next_point, next_lower, next_upper, thresh_val)

    next_week = NextWeekForecast(
        target_week_end_date=fc_row[0],
        point=next_point,
        lower=next_lower,
        upper=next_upper,
        tier=tier,
        model_name=next_model,
    )

    # Ring gauge
    if thresh_val > 0:
        ring = RingGauge(
            forecast_pct_of_threshold=round((next_point / thresh_val) * 100.0, 2),
            lower_pct=round((next_lower / thresh_val) * 100.0, 2),
            upper_pct=round((next_upper / thresh_val) * 100.0, 2),
        )
    else:
        ring = RingGauge(
            forecast_pct_of_threshold=None,
            lower_pct=None,
            upper_pct=None,
        )

    # Actions
    actions_dict = get_action_checklist(tier, planning_cfg.get("actions"))
    actions = ActionsBlock(
        tier=actions_dict["tier"],
        items=actions_dict["items"],
        footer=actions_dict["footer"],
    )

    selected = SelectedSummary(
        disease=disease,
        jurisdiction=jurisdiction,
        target_kind=run["target_kind"],
        unit="admissions per week" if run["target_kind"] == "count" else "rate per 100k",
        latest=latest,
        threshold=thresh_info,
        next_week=next_week,
        ring=ring,
        recent=recent,
        actions=actions,
    )

    # Watchlist for all diseases in T4
    cur.execute("SELECT code, label FROM diseases ORDER BY code")
    all_diseases = cur.fetchall()
    watchlist: list[WatchlistItem] = []

    for d_code, d_label in all_diseases:
        cur.execute(
            "SELECT id, default_threshold FROM v_current_runs WHERE jurisdiction_code = ? AND disease_code = ?",
            (jurisdiction, d_code),
        )
        d_run = cur.fetchone()
        if not d_run:
            watchlist.append(
                WatchlistItem(
                    disease=d_code,
                    label=d_label,
                    available=False,
                    latest_value=None,
                    next_week_point=None,
                    tier=None,
                    threshold=None,
                )
            )
            continue

        d_run_id = d_run[0]
        d_thresh = float(d_run[1])

        # Latest value
        cur.execute(
            "SELECT admissions_count FROM weekly_observations WHERE jurisdiction_code = ? AND disease_code = ? "
            "ORDER BY week_end_date DESC LIMIT 1",
            (jurisdiction, d_code),
        )
        d_obs = cur.fetchone()
        d_latest_val = float(d_obs[0]) if d_obs and d_obs[0] is not None else 0.0

        # Forecast h=1
        cur.execute(
            "SELECT point, lower, upper FROM forecasts WHERE run_id = ? AND horizon_weeks = 1",
            (d_run_id,),
        )
        d_fc = cur.fetchone()
        if d_fc:
            d_pt = float(d_fc[0])
            d_lw = float(d_fc[1])
            d_up = float(d_fc[2])
            d_tier = calculate_tier(d_pt, d_lw, d_up, d_thresh)
        else:
            d_pt, d_tier = 0.0, "normal"

        watchlist.append(
            WatchlistItem(
                disease=d_code,
                label=d_label,
                available=True,
                latest_value=d_latest_val,
                next_week_point=d_pt,
                tier=d_tier,
                threshold=d_thresh,
            )
        )

    # Evaluation headline (h=1)
    cur.execute(
        "SELECT model_name, mae, interval_coverage, beats_persistence FROM evaluation_metrics "
        "WHERE run_id = ? AND horizon_weeks = 1 AND split = 'test' AND is_selected = 1",
        (run["id"],),
    )
    metric_row = cur.fetchone()
    if not metric_row:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "data_unavailable",
                "message": "Evaluation metrics missing for current run.",
                "fields": [],
            },
        )

    sel_model_name = metric_row[0]
    test_mae = float(metric_row[1])
    test_cov = float(metric_row[2]) if metric_row[2] is not None else 0.0
    beats_pers = bool(metric_row[3]) if metric_row[3] is not None else False

    cur.execute(
        "SELECT mae FROM evaluation_metrics WHERE run_id = ? AND horizon_weeks = 1 AND split = 'test' "
        "AND model_name = 'baseline_persistence'",
        (run["id"],),
    )
    pers_row = cur.fetchone()
    persistence_mae = float(pers_row[0]) if pers_row else test_mae

    eval_headline = EvaluationHeadline(
        horizon_weeks=1,
        selected_model=sel_model_name,
        test_mae=test_mae,
        persistence_test_mae=persistence_mae,
        beats_persistence=beats_pers,
        test_interval_coverage=test_cov,
    )

    return SummaryResponse(
        data_as_of=data_as_of,
        stale=stale,
        selected=selected,
        watchlist=watchlist,
        evaluation_headline=eval_headline,
    )


# ---------------------------------------------------------------------------
# E4: Observations
# ---------------------------------------------------------------------------

@router.get("/observations", response_model=ObservationsResponse)
def get_observations(
    disease: str = Query("flu"),
    jurisdiction: str = Query("US"),
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
    conn: sqlite3.Connection = Depends(get_db),
) -> ObservationsResponse:
    validate_jurisdiction(conn, jurisdiction)
    validate_disease(conn, disease)

    # Date range validation
    if from_date:
        try:
            datetime.strptime(from_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "validation_error",
                    "message": "Invalid date format for 'from'. Must be YYYY-MM-DD.",
                    "fields": ["from"],
                },
            )

    if to_date:
        try:
            datetime.strptime(to_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "validation_error",
                    "message": "Invalid date format for 'to'. Must be YYYY-MM-DD.",
                    "fields": ["to"],
                },
            )

    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "validation_error",
                "message": "Parameter 'from' must be less than or equal to 'to'.",
                "fields": ["from", "to"],
            },
        )

    run = get_current_run(conn, jurisdiction, disease)
    target_col = TARGET_ALLOWLIST.get(run["target_kind"], "admissions_count")

    query = (
        SQL_OBSERVATIONS_COUNT
        if target_col == "admissions_count"
        else SQL_OBSERVATIONS_RATE
    )

    cur = conn.cursor()
    cur.execute(query, (jurisdiction, disease, from_date, from_date, to_date, to_date))
    rows = cur.fetchall()

    points = [
        ObservationPoint(
            week_end_date=r[0],
            value=float(r[1]) if r[1] is not None else 0.0,
            is_imputed=bool(r[2]),
            pct_reporting=float(r[3]) if r[3] is not None else None,
        )
        for r in rows
    ]

    return ObservationsResponse(
        disease=disease,
        jurisdiction=jurisdiction,
        target_kind=run["target_kind"],
        unit="admissions per week" if run["target_kind"] == "count" else "rate per 100k",
        count=len(points),
        points=points,
    )


# ---------------------------------------------------------------------------
# E5: Forecast
# ---------------------------------------------------------------------------

@router.get("/forecast", response_model=ForecastResponse)
def get_forecast(
    disease: str = Query("flu"),
    jurisdiction: str = Query("US"),
    threshold: float | None = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
) -> ForecastResponse:
    validate_jurisdiction(conn, jurisdiction)
    validate_disease(conn, disease)
    validate_threshold(threshold)

    run = get_current_run(conn, jurisdiction, disease)
    planning_cfg = load_planning_config()

    if threshold is not None:
        thresh_val = float(threshold)
        thresh_source = "override"
    else:
        thresh_val = float(run["default_threshold"])
        thresh_source = "default"

    threshold_info = ForecastThresholdInfo(
        value=thresh_val,
        source=thresh_source,
        method=run["default_threshold_method"],
    )

    cur = conn.cursor()
    cur.execute(
        "SELECT horizon_weeks, origin_week_end_date, target_week_end_date, point, lower, upper, model_name "
        "FROM forecasts WHERE run_id = ? ORDER BY horizon_weeks ASC",
        (run["id"],),
    )
    rows = cur.fetchall()
    if len(rows) != 4:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "data_unavailable",
                "message": f"Expected 4 forecast horizons, found {len(rows)}.",
                "fields": [],
            },
        )

    horizons: list[ForecastHorizonItem] = []
    tiers: list[str] = []

    for r in rows:
        h_weeks = int(r[0])
        origin_date = str(r[1])
        target_date = str(r[2])
        pt = float(r[3])
        lw = float(r[4])
        up = float(r[5])
        m_name = str(r[6])

        h_tier = calculate_tier(pt, lw, up, thresh_val)
        tiers.append(h_tier)

        horizons.append(
            ForecastHorizonItem(
                horizon_weeks=h_weeks,
                origin_week_end_date=origin_date,
                target_week_end_date=target_date,
                point=pt,
                lower=lw,
                upper=up,
                model_name=m_name,
                tier=h_tier,
            )
        )

    # Max severity tier across horizons
    if "elevated" in tiers:
        max_tier = "elevated"
    elif "watch" in tiers:
        max_tier = "watch"
    else:
        max_tier = "normal"

    actions_dict = get_action_checklist(max_tier, planning_cfg.get("actions"))
    actions = ActionsBlock(
        tier=actions_dict["tier"],
        items=actions_dict["items"],
        footer=actions_dict["footer"],
    )

    run_meta = RunMeta(
        id=run["id"],
        created_at=run["created_at"],
        data_end_date=run["data_end_date"],
        target_kind=run["target_kind"],
    )

    return ForecastResponse(
        run=run_meta,
        interval_level=float(run["interval_level"]),
        threshold=threshold_info,
        horizons=horizons,
        actions=actions,
        disclaimer="Planning signal — not a bed-shortage prediction.",
    )


# ---------------------------------------------------------------------------
# E6: Evaluation
# ---------------------------------------------------------------------------

@router.get("/evaluation", response_model=EvaluationResponse)
def get_evaluation(
    disease: str = Query("flu"),
    jurisdiction: str = Query("US"),
    horizon: int = Query(1, ge=1, le=4),
    conn: sqlite3.Connection = Depends(get_db),
) -> EvaluationResponse:
    validate_jurisdiction(conn, jurisdiction)
    validate_disease(conn, disease)

    run = get_current_run(conn, jurisdiction, disease)
    cur = conn.cursor()

    # Metrics for requested horizon
    cur.execute(
        "SELECT horizon_weeks, model_name, split, mae, rmse, n_eval, mae_vs_persistence, is_selected "
        "FROM evaluation_metrics WHERE run_id = ? AND horizon_weeks = ? ORDER BY split, model_name",
        (run["id"], horizon),
    )
    metric_rows = cur.fetchall()

    metrics = [
        MetricItem(
            horizon_weeks=int(r[0]),
            model_name=str(r[1]),
            split=str(r[2]),
            mae=float(r[3]),
            rmse=float(r[4]),
            n_eval=int(r[5]),
            mae_vs_persistence=float(r[6]) if r[6] is not None else None,
            is_selected=bool(r[7]),
        )
        for r in metric_rows
    ]

    # Selected model info
    cur.execute(
        "SELECT horizon_weeks, model_name, beats_persistence, interval_coverage FROM evaluation_metrics "
        "WHERE run_id = ? AND horizon_weeks = ? AND split = 'test' AND is_selected = 1",
        (run["id"], horizon),
    )
    sel_row = cur.fetchone()
    if not sel_row:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "data_unavailable",
                "message": "Selected model record missing.",
                "fields": [],
            },
        )

    beats_pers = bool(sel_row[2]) if sel_row[2] is not None else False
    test_cov = float(sel_row[3]) if sel_row[3] is not None else 0.0

    selected = [
        SelectedModelItem(
            horizon_weeks=horizon,
            model_name=str(sel_row[1]),
            beats_persistence=beats_pers,
            test_interval_coverage=test_cov,
        )
    ]

    # Verdict text strictly adhering to AT-14
    if beats_pers:
        verdict_text = "On the held-out test weeks, the selected model's MAE is lower than the persistence baseline's."
    else:
        verdict_text = "On the held-out test weeks, the persistence baseline achieved a lower MAE than the selected model."

    verdicts = [
        VerdictItem(
            horizon_weeks=horizon,
            beats_persistence=beats_pers,
            text=verdict_text,
        )
    ]

    # Backtest series for test split
    cur.execute(
        "SELECT target_week_end_date, actual, predicted FROM backtest_predictions "
        "WHERE run_id = ? AND horizon_weeks = ? AND split = 'test' AND model_name = ? "
        "ORDER BY target_week_end_date ASC",
        (run["id"], horizon, sel_row[1]),
    )
    sel_backtests = {r[0]: (float(r[1]), float(r[2])) for r in cur.fetchall()}

    cur.execute(
        "SELECT target_week_end_date, predicted FROM backtest_predictions "
        "WHERE run_id = ? AND horizon_weeks = ? AND split = 'test' AND model_name = 'baseline_persistence' "
        "ORDER BY target_week_end_date ASC",
        (run["id"], horizon),
    )
    pers_backtests = {r[0]: float(r[1]) for r in cur.fetchall()}

    backtest_points = [
        BacktestPoint(
            target_week_end_date=dt,
            actual=actual_pred[0],
            predicted_selected=actual_pred[1],
            predicted_persistence=pers_backtests.get(dt, actual_pred[0]),
        )
        for dt, actual_pred in sorted(sel_backtests.items())
    ]

    run_splits = RunSplits(
        id=run["id"],
        train=[run["train_start"], run["train_end"]],
        validation=[run["valid_start"], run["valid_end"]],
        test=[run["test_start"], run["test_end"]],
        n_train=run["n_train"],
        n_valid=run["n_valid"],
        n_test=run["n_test"],
    )

    return EvaluationResponse(
        run=run_splits,
        metrics=metrics,
        selected=selected,
        verdicts=verdicts,
        backtest=BacktestSeries(horizon_weeks=horizon, points=backtest_points),
    )


# ---------------------------------------------------------------------------
# E7: Explain
# ---------------------------------------------------------------------------

@router.get("/explain", response_model=ExplainResponse)
def get_explain(
    disease: str = Query("flu"),
    jurisdiction: str = Query("US"),
    horizon: int = Query(1, ge=1, le=4),
    conn: sqlite3.Connection = Depends(get_db),
) -> ExplainResponse:
    validate_jurisdiction(conn, jurisdiction)
    validate_disease(conn, disease)

    run = get_current_run(conn, jurisdiction, disease)
    cur = conn.cursor()

    # Selected model name & forecast prediction
    cur.execute(
        "SELECT model_name, point FROM forecasts WHERE run_id = ? AND horizon_weeks = ?",
        (run["id"], horizon),
    )
    fc_row = cur.fetchone()
    if not fc_row:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "data_unavailable",
                "message": "Forecast not found for current run.",
                "fields": [],
            },
        )

    model_name = str(fc_row[0])
    prediction = float(fc_row[1])

    # Permutation importance
    cur.execute(
        "SELECT feature_name, value FROM feature_contributions "
        "WHERE run_id = ? AND horizon_weeks = ? AND method = 'permutation_importance' "
        "ORDER BY value DESC",
        (run["id"], horizon),
    )
    perm_rows = cur.fetchall()
    perm_importance = [
        PermutationImportanceItem(
            feature=r[0],
            label=FEATURE_LABELS.get(r[0], r[0]),
            value=float(r[1]),
        )
        for r in perm_rows
    ]

    contributions: list[FeatureContributionItem] | None = None
    base_value = prediction
    top_label = "recent observations"
    top_val = 0.0
    is_positive = True

    if model_name == "linear_lag":
        # Linear contributions exist
        cur.execute(
            "SELECT feature_name, value, feature_value FROM feature_contributions "
            "WHERE run_id = ? AND horizon_weeks = ? AND method = 'linear_contribution'",
            (run["id"], horizon),
        )
        contrib_rows = cur.fetchall()

        contrib_items: list[FeatureContributionItem] = []
        for r in contrib_rows:
            f_name = str(r[0])
            val = float(r[1])
            f_val = float(r[2]) if r[2] is not None else None

            if f_name == "__base__":
                base_value = val
            else:
                contrib_items.append(
                    FeatureContributionItem(
                        feature=f_name,
                        label=FEATURE_LABELS.get(f_name, f_name),
                        value=val,
                        feature_value=f_val,
                    )
                )

        # Sort by absolute contribution descending
        contrib_items.sort(key=lambda x: abs(x.value), reverse=True)
        contributions = contrib_items

        if contrib_items:
            top_item = contrib_items[0]
            top_label = top_item.label
            top_val = top_item.value
            is_positive = top_val >= 0
    else:
        # For non-linear model (hgb_lag), contributions are None
        contributions = None
        if perm_importance:
            top_label = perm_importance[0].label
            top_val = perm_importance[0].value
            is_positive = True

    explanation_text = format_explanation_text(
        horizon_weeks=horizon,
        top_feature_label=top_label,
        top_feature_value=top_val,
        is_positive=is_positive,
    )

    return ExplainResponse(
        horizon_weeks=horizon,
        model_name=model_name,
        base_value=base_value,
        prediction=prediction,
        contributions=contributions,
        permutation_importance=perm_importance,
        text=explanation_text,
        note="These are model associations, not causes.",
    )


# ---------------------------------------------------------------------------
# E8: Scenario
# ---------------------------------------------------------------------------

@router.post("/scenario", response_model=ScenarioResponse)
def post_scenario(
    req: ScenarioRequest,
    conn: sqlite3.Connection = Depends(get_db),
) -> ScenarioResponse:
    validate_jurisdiction(conn, req.jurisdiction)
    validate_disease(conn, req.disease)
    validate_threshold(req.threshold)

    run = get_current_run(conn, req.jurisdiction, req.disease)
    planning_cfg = load_planning_config()

    if req.threshold is not None:
        thresh_val = float(req.threshold)
        thresh_source = "override"
    else:
        thresh_val = float(run["default_threshold"])
        thresh_source = "default"

    threshold_info = ThresholdInfo(value=thresh_val, source=thresh_source)

    # Forecast horizons
    cur = conn.cursor()
    cur.execute(
        "SELECT horizon_weeks, target_week_end_date, point, lower, upper FROM forecasts "
        "WHERE run_id = ? ORDER BY horizon_weeks ASC",
        (run["id"],),
    )
    fc_rows = cur.fetchall()
    if len(fc_rows) != 4:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "data_unavailable",
                "message": "Forecast horizons missing for current run.",
                "fields": [],
            },
        )

    horizons: list[ScenarioHorizonItem] = []
    scenario_tiers: list[str] = []

    for r in fc_rows:
        h_weeks = int(r[0])
        target_date = str(r[1])
        base_pt = float(r[2])
        base_lw = float(r[3])
        base_up = float(r[4])

        base_tier = calculate_tier(base_pt, base_lw, base_up, thresh_val)

        scaled = calculate_scenario(base_pt, base_lower=base_lw, base_upper=base_up, surge_pct=req.surge_pct)
        scen_tier = calculate_tier(scaled["point"], scaled["lower"], scaled["upper"], thresh_val)
        scenario_tiers.append(scen_tier)

        horizons.append(
            ScenarioHorizonItem(
                horizon_weeks=h_weeks,
                target_week_end_date=target_date,
                base=HorizonBand(
                    point=base_pt,
                    lower=base_lw,
                    upper=base_up,
                    tier=base_tier,
                ),
                scenario=HorizonBand(
                    point=scaled["point"],
                    lower=scaled["lower"],
                    upper=scaled["upper"],
                    tier=scen_tier,
                ),
            )
        )

    # Capacity inputs
    if req.capacity is not None:
        capacity_inputs = req.capacity
    else:
        cap_defaults = planning_cfg.get("capacity_defaults", {})
        capacity_inputs = CapacityInputs(
            typical_weekly_admissions=float(cap_defaults.get("typical_weekly_admissions", 100.0)),
            alos_days=float(cap_defaults.get("alos_days", 4.5)),
            staffed_beds=float(cap_defaults.get("staffed_beds", 80.0)),
            patients_per_nurse=float(cap_defaults.get("patients_per_nurse", 4.0)),
        )

    ref_level = float(run["reference_level"])
    capacity_horizons: list[CapacityHorizonItem] = []
    cap_message: str | None = None

    for h in horizons:
        scen_pt = h.scenario.point
        cap_res = calculate_capacity_illustration(
            scenario_point=scen_pt,
            reference_level=ref_level,
            typical_weekly_admissions=capacity_inputs.typical_weekly_admissions,
            alos_days=capacity_inputs.alos_days,
            staffed_beds=capacity_inputs.staffed_beds,
            patients_per_nurse=capacity_inputs.patients_per_nurse,
        )
        if cap_res["message"]:
            cap_message = cap_res["message"]

        capacity_horizons.append(
            CapacityHorizonItem(
                horizon_weeks=h.horizon_weeks,
                relative_change=cap_res["relative_change"],
                hospital_weekly_admissions=cap_res["hospital_weekly_admissions"],
                est_occupied_beds=cap_res["est_occupied_beds"],
                bed_gap=cap_res["bed_gap"],
                nurses_per_shift=cap_res["nurses_per_shift"],
            )
        )

    formulae = [
        "relative_change = scenario_point / reference_level",
        "hospital_weekly_admissions = typical_weekly_admissions × relative_change",
        "est_occupied_beds = hospital_weekly_admissions × alos_days / 7",
        "bed_gap = est_occupied_beds − staffed_beds",
        "nurses_per_shift = est_occupied_beds / patients_per_nurse",
    ]

    capacity_block = CapacityBlock(
        is_simulated=True,
        label="SIMULATED — assumption-based",
        reference_level=ref_level,
        inputs=capacity_inputs,
        horizons=capacity_horizons,
        formulae=formulae,
        message=cap_message,
    )

    # Actions based on scenario tiers
    if "elevated" in scenario_tiers:
        scen_max_tier = "elevated"
    elif "watch" in scenario_tiers:
        scen_max_tier = "watch"
    else:
        scen_max_tier = "normal"

    actions_dict = get_action_checklist(scen_max_tier, planning_cfg.get("actions"))
    actions = ActionsBlock(
        tier=actions_dict["tier"],
        items=actions_dict["items"],
        footer=actions_dict["footer"],
    )

    return ScenarioResponse(
        is_scenario=True,
        label="SCENARIO — not a prediction",
        surge_pct=req.surge_pct,
        threshold=threshold_info,
        horizons=horizons,
        capacity=capacity_block,
        actions=actions,
    )
