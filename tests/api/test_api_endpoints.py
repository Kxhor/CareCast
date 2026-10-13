"""Endpoint tests for CareCast API v1 (Phase 4).

Acceptance tests covered:
- AT-06: GET /observations ascending dates, from > to -> 422, bounded results
- AT-09: GET /forecast 4 horizons ascending, lower <= point <= upper, target = origin + 7*h days
- AT-10 (API): Empirical coverage exposed in evaluation
- AT-16: Non-numeric, negative, NaN/inf, > bound threshold -> 422
- AT-22: surge_pct outside [-50, 100] -> 422
- AT-25 (API): is_simulated=true in /scenario response
- AT-28: /meta returns provenance, dataset id, sha256, data_as_of, disclaimers
- AT-30: /summary returns latest, next-week forecast, tier, and watchlist
"""

import pytest
from fastapi.testclient import TestClient
from carecast.api.main import create_app
from carecast.settings import Settings


@pytest.fixture(scope="module")
def client():
    # Use real database data/carecast.db in test settings
    settings = Settings(
        env="dev",
        db_path="data/carecast.db",
        enable_docs=True,
        rate_get_per_min=1000,
        rate_post_per_min=500,
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


class TestHealthE1:
    def test_health_ok(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["db_ok"] is True
        assert "data_as_of" in data
        assert data["version"] == "0.1.0"


class TestMetaE2AT28:
    """AT-28: /meta returns provenance, dataset id, sha256, data_as_of, disclaimers."""

    def test_meta_contract(self, client):
        resp = client.get("/api/v1/meta")
        assert resp.status_code == 200
        data = resp.json()

        # Provenance & app
        assert data["app"]["name"] == "CareCast"
        assert data["data_as_of"] == "2026-10-03"
        assert "source" in data
        assert len(data["source"]["file_sha256"]) == 64
        assert data["source"]["publisher"] != ""

        # Diseases and jurisdictions
        disease_codes = [d["code"] for d in data["diseases"]]
        assert "flu" in disease_codes
        assert "covid19" in disease_codes
        assert "rsv" in disease_codes

        jurisdictions = [j["code"] for j in data["jurisdictions"]]
        assert "US" in jurisdictions

        # Horizons and defaults
        assert data["horizons"] == [1, 2, 3, 4]
        assert data["defaults"]["interval_level"] == 0.8
        assert data["defaults"]["capacity"]["is_simulated"] is True
        assert "DEMO PLACEHOLDER" in data["defaults"]["capacity"]["note"]

        # Limitations L-01 to L-12
        lim_ids = [lim["id"] for lim in data["limitations"]]
        for i in range(1, 13):
            assert f"L-{i:02d}" in lim_ids

        # Disclaimer
        assert "Not clinically validated" in data["disclaimer"]


class TestSummaryE3AT30:
    """AT-30: /summary returns latest, next-week forecast, tier, and watchlist."""

    def test_summary_success(self, client):
        resp = client.get("/api/v1/summary?disease=flu&jurisdiction=US")
        assert resp.status_code == 200
        data = resp.json()

        assert "data_as_of" in data
        assert "stale" in data
        assert data["selected"]["disease"] == "flu"
        assert data["selected"]["jurisdiction"] == "US"
        assert data["selected"]["latest"]["value"] > 0
        assert "change_pct_vs_prior_week" in data["selected"]["latest"]

        # Next week forecast & tier
        next_wk = data["selected"]["next_week"]
        assert next_wk["point"] >= 0
        assert next_wk["lower"] <= next_wk["point"] <= next_wk["upper"]
        assert next_wk["tier"] in {"normal", "watch", "elevated"}

        # Ring gauge
        assert "forecast_pct_of_threshold" in data["selected"]["ring"]

        # Recent 8 weeks
        assert len(data["selected"]["recent"]) == 8
        # Ensure chronological ascending
        dates = [r["week_end_date"] for r in data["selected"]["recent"]]
        assert dates == sorted(dates)

        # Watchlist
        assert len(data["watchlist"]) >= 3
        watchlist_diseases = [w["disease"] for w in data["watchlist"]]
        assert "flu" in watchlist_diseases
        assert "covid19" in watchlist_diseases
        assert "rsv" in watchlist_diseases

        # Evaluation headline
        assert data["evaluation_headline"]["horizon_weeks"] == 1
        assert "beats_persistence" in data["evaluation_headline"]

    def test_summary_threshold_override(self, client):
        resp = client.get("/api/v1/summary?disease=flu&threshold=500.0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["selected"]["threshold"]["value"] == 500.0
        assert data["selected"]["threshold"]["source"] == "override"


class TestObservationsE4AT06:
    """AT-06: GET /observations returns ascending dates; from > to -> 422; filters bound the result."""

    def test_observations_ascending(self, client):
        resp = client.get("/api/v1/observations?disease=flu&jurisdiction=US")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] > 0
        dates = [p["week_end_date"] for p in data["points"]]
        assert dates == sorted(dates)
        assert len(data["points"]) == data["count"]

    def test_observations_date_filters(self, client):
        resp = client.get(
            "/api/v1/observations?disease=flu&jurisdiction=US&from=2024-01-06&to=2024-03-30"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] > 0
        for p in data["points"]:
            assert "2024-01-06" <= p["week_end_date"] <= "2024-03-30"

    def test_observations_from_greater_than_to_returns_422(self, client):
        resp = client.get(
            "/api/v1/observations?disease=flu&jurisdiction=US&from=2024-05-01&to=2024-01-01"
        )
        assert resp.status_code == 422
        err = resp.json()
        assert err["error"]["code"] == "validation_error"

    def test_observations_empty_range_returns_200(self, client):
        resp = client.get(
            "/api/v1/observations?disease=flu&jurisdiction=US&from=1990-01-01&to=1990-02-01"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["points"] == []


class TestForecastE5AT09:
    """AT-09: GET /forecast returns 4 horizons ascending; lower <= point <= upper; target = origin + 7*h days."""

    def test_forecast_horizons_structure(self, client):
        from datetime import datetime, timedelta

        resp = client.get("/api/v1/forecast?disease=flu&jurisdiction=US")
        assert resp.status_code == 200
        data = resp.json()

        horizons = data["horizons"]
        assert len(horizons) == 4
        assert [h["horizon_weeks"] for h in horizons] == [1, 2, 3, 4]

        for h in horizons:
            assert h["lower"] <= h["point"] <= h["upper"]
            assert h["lower"] >= 0
            assert h["tier"] in {"normal", "watch", "elevated"}
            # Date relationship: target = origin + 7 * h days
            origin_dt = datetime.strptime(h["origin_week_end_date"], "%Y-%m-%d")
            target_dt = datetime.strptime(h["target_week_end_date"], "%Y-%m-%d")
            expected_target = origin_dt + timedelta(days=7 * h["horizon_weeks"])
            assert target_dt == expected_target

        assert data["actions"]["tier"] in {"normal", "watch", "elevated"}
        assert len(data["actions"]["items"]) >= 3
        assert "Final decisions" in data["actions"]["footer"]
        assert "Planning signal" in data["disclaimer"]


class TestEvaluationE6AT10:
    """AT-10 (API): Empirical coverage on the test block is exposed and metrics present."""

    def test_evaluation_structure(self, client):
        resp = client.get("/api/v1/evaluation?disease=flu&jurisdiction=US&horizon=1")
        assert resp.status_code == 200
        data = resp.json()

        assert data["run"]["n_train"] > 0
        assert data["run"]["n_valid"] > 0
        assert data["run"]["n_test"] > 0

        # Metrics exist for models
        model_names = {m["model_name"] for m in data["metrics"]}
        assert "baseline_persistence" in model_names
        assert "linear_lag" in model_names

        # Selected model has test interval coverage exposed
        assert len(data["selected"]) >= 1
        sel = data["selected"][0]
        assert sel["horizon_weeks"] == 1
        assert 0.0 <= sel["test_interval_coverage"] <= 1.0

        # Verdict text is present
        assert len(data["verdicts"]) >= 1
        assert "test weeks" in data["verdicts"][0]["text"].lower()

        # Backtest points exist
        assert len(data["backtest"]["points"]) > 0
        assert data["backtest"]["horizon_weeks"] == 1


class TestExplainE7:
    def test_explain_linear_model(self, client):
        resp = client.get("/api/v1/explain?disease=flu&jurisdiction=US&horizon=1")
        assert resp.status_code == 200
        data = resp.json()

        assert data["horizon_weeks"] == 1
        assert data["model_name"] == "linear_lag"
        assert data["base_value"] >= 0
        assert data["prediction"] >= 0
        assert data["contributions"] is not None
        assert len(data["contributions"]) > 0

        # Linear identity check AT-18
        contrib_sum = sum(c["value"] for c in data["contributions"])
        assert abs(data["base_value"] + contrib_sum - data["prediction"]) < 1e-6

        # Permutation importance
        assert len(data["permutation_importance"]) > 0
        assert "associated with" in data["text"]
        assert data["note"] == "These are model associations, not causes."


class TestScenarioE8AT22AT25:
    """AT-22: surge_pct outside [-50, 100] -> 422.
    AT-25 (API): is_simulated=true in /scenario response.
    """

    def test_scenario_valid_custom_capacity(self, client):
        payload = {
            "disease": "flu",
            "jurisdiction": "US",
            "surge_pct": 20.0,
            "threshold": 10000.0,
            "capacity": {
                "typical_weekly_admissions": 100.0,
                "alos_days": 4.5,
                "staffed_beds": 80.0,
                "patients_per_nurse": 4.0,
            },
        }
        resp = client.post("/api/v1/scenario", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["is_scenario"] is True
        assert data["label"] == "SCENARIO — not a prediction"
        assert data["surge_pct"] == 20.0

        # AT-25 (API)
        assert data["capacity"]["is_simulated"] is True
        assert "SIMULATED" in data["capacity"]["label"]

        # Horizons have base and scenario
        assert len(data["horizons"]) == 4
        h1 = data["horizons"][0]
        assert h1["scenario"]["point"] == pytest.approx(h1["base"]["point"] * 1.2, rel=1e-5)

        # Capacity metrics
        cap_h1 = data["capacity"]["horizons"][0]
        assert cap_h1["relative_change"] is not None
        assert cap_h1["hospital_weekly_admissions"] is not None

    def test_scenario_default_capacity_when_null(self, client):
        payload = {
            "disease": "flu",
            "jurisdiction": "US",
            "surge_pct": 10.0,
            "threshold": None,
            "capacity": None,
        }
        resp = client.post("/api/v1/scenario", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["capacity"]["inputs"]["typical_weekly_admissions"] == 100.0

    @pytest.mark.parametrize("surge_pct", [-51.0, 101.0, -100.0, 500.0])
    def test_scenario_invalid_surge_pct_returns_422(self, client, surge_pct):
        payload = {
            "disease": "flu",
            "jurisdiction": "US",
            "surge_pct": surge_pct,
        }
        resp = client.post("/api/v1/scenario", json=payload)
        assert resp.status_code == 422
        err = resp.json()
        assert err["error"]["code"] == "validation_error"


class TestThresholdInputSanityAT16:
    """AT-16: Non-numeric, negative, NaN/inf, > bound threshold -> 422."""

    @pytest.mark.parametrize("bad_thresh", ["abc", "-5.0", "1e10", "inf", "nan", "-inf"])
    def test_summary_bad_threshold(self, client, bad_thresh):
        resp = client.get(f"/api/v1/summary?disease=flu&threshold={bad_thresh}")
        assert resp.status_code == 422
        err = resp.json()
        assert err["error"]["code"] == "validation_error"

    @pytest.mark.parametrize("bad_thresh", ["abc", "-1.0", "1e11"])
    def test_forecast_bad_threshold(self, client, bad_thresh):
        resp = client.get(f"/api/v1/forecast?disease=flu&threshold={bad_thresh}")
        assert resp.status_code == 422
        err = resp.json()
        assert err["error"]["code"] == "validation_error"
