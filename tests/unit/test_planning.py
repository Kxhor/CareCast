"""Unit tests for carecast.planning (Phase 4).

Acceptance tests covered:
- AT-15: Tier boundary table
- AT-19: Explanation text non-causal language
- AT-21: Scenario scaling formula
- AT-24: Capacity illustration worked example & zero reference level
- AT-26: Fixed deterministic action checklists by tier
"""

import math
import pytest
from carecast.planning import (
    calculate_tier,
    calculate_scenario,
    calculate_capacity_illustration,
    get_action_checklist,
    format_explanation_text,
    FORBIDDEN_CAUSAL_WORDS,
)


class TestTierBoundaryTableAT15:
    """AT-15: Boundary table tests for calculate_tier.
    
    PRD F5.2 rules:
      - Elevated if point > threshold
      - Watch if point <= threshold < upper
      - Normal if upper <= threshold
    """

    def test_point_above_threshold_is_elevated(self):
        # point > threshold
        assert calculate_tier(point=101.0, lower=80.0, upper=120.0, threshold=100.0) == "elevated"

    def test_point_equals_threshold_is_watch_when_upper_exceeds(self):
        # point == threshold and upper > threshold -> Watch
        assert calculate_tier(point=100.0, lower=80.0, upper=120.0, threshold=100.0) == "watch"

    def test_point_below_threshold_and_upper_above_is_watch(self):
        # point < threshold < upper -> Watch
        assert calculate_tier(point=90.0, lower=80.0, upper=110.0, threshold=100.0) == "watch"

    def test_upper_equals_threshold_is_normal(self):
        # upper == threshold -> Normal
        assert calculate_tier(point=80.0, lower=60.0, upper=100.0, threshold=100.0) == "normal"

    def test_upper_below_threshold_is_normal(self):
        # upper < threshold -> Normal
        assert calculate_tier(point=70.0, lower=50.0, upper=90.0, threshold=100.0) == "normal"

    def test_point_and_upper_equal_threshold_is_normal(self):
        # point == upper == threshold -> upper <= threshold -> Normal
        assert calculate_tier(point=100.0, lower=100.0, upper=100.0, threshold=100.0) == "normal"

    @pytest.mark.parametrize(
        "point,lower,upper,threshold,expected",
        [
            (100.001, 80.0, 120.0, 100.0, "elevated"),
            (100.0, 80.0, 100.001, 100.0, "watch"),
            (99.999, 80.0, 100.0, 100.0, "normal"),
            (0.0, 0.0, 0.0, 0.0, "normal"),
            (10.0, 5.0, 15.0, 0.0, "elevated"),
        ],
    )
    def test_boundary_precision(self, point, lower, upper, threshold, expected):
        assert calculate_tier(point=point, lower=lower, upper=upper, threshold=threshold) == expected


class TestScenarioScalingAT21:
    """AT-21: Scenario scaling formula tests.
    
    adjusted = base * (1 + pct / 100) for point/lower/upper; pct=0 equals base.
    """

    def test_zero_surge_equals_base(self):
        res = calculate_scenario(base_point=100.0, base_lower=80.0, base_upper=120.0, surge_pct=0.0)
        assert res["point"] == 100.0
        assert res["lower"] == 80.0
        assert res["upper"] == 120.0

    def test_positive_surge(self):
        res = calculate_scenario(base_point=100.0, base_lower=80.0, base_upper=120.0, surge_pct=25.0)
        assert math.isclose(res["point"], 125.0)
        assert math.isclose(res["lower"], 100.0)
        assert math.isclose(res["upper"], 150.0)

    def test_negative_surge(self):
        res = calculate_scenario(base_point=100.0, base_lower=80.0, base_upper=120.0, surge_pct=-50.0)
        assert math.isclose(res["point"], 50.0)
        assert math.isclose(res["lower"], 40.0)
        assert math.isclose(res["upper"], 60.0)

    def test_non_negative_guarantee(self):
        res = calculate_scenario(base_point=0.0, base_lower=0.0, base_upper=0.0, surge_pct=100.0)
        assert res["point"] == 0.0
        assert res["lower"] == 0.0
        assert res["upper"] == 0.0


class TestCapacityIllustrationAT24:
    """AT-24: Worked example yields the formula results exactly."""

    def test_worked_example(self):
        # typical 100/wk, relative_change 1.2, ALOS 5, ratio 6 (staffed_beds=80)
        # scenario_point = 120, reference_level = 100 -> relative_change = 1.2
        # hospital_weekly_admissions = 100 * 1.2 = 120
        # est_occupied_beds = 120 * 5 / 7 = 85.71428571428571
        # bed_gap = est_occupied_beds - 80 = 5.71428571428571
        # nurses_per_shift = est_occupied_beds / 6 = 14.285714285714285
        res = calculate_capacity_illustration(
            scenario_point=120.0,
            reference_level=100.0,
            typical_weekly_admissions=100.0,
            alos_days=5.0,
            staffed_beds=80.0,
            patients_per_nurse=6.0,
        )
        assert res["relative_change"] == pytest.approx(1.2, rel=1e-5)
        assert res["hospital_weekly_admissions"] == pytest.approx(120.0, rel=1e-5)
        assert res["est_occupied_beds"] == pytest.approx(85.7142857, rel=1e-5)
        assert res["bed_gap"] == pytest.approx(5.7142857, rel=1e-5)
        assert res["nurses_per_shift"] == pytest.approx(14.2857143, rel=1e-5)
        assert res["message"] is None

    def test_reference_level_zero_handled_safely(self):
        res = calculate_capacity_illustration(
            scenario_point=120.0,
            reference_level=0.0,
            typical_weekly_admissions=100.0,
            alos_days=5.0,
            staffed_beds=80.0,
            patients_per_nurse=6.0,
        )
        assert res["relative_change"] is None
        assert res["hospital_weekly_admissions"] is None
        assert res["est_occupied_beds"] is None
        assert res["bed_gap"] is None
        assert res["nurses_per_shift"] is None
        assert "zero" in res["message"].lower()


class TestActionChecklistAT26:
    """AT-26: Each tier returns a fixed, deterministic checklist ending with standard footer."""

    def test_deterministic_checklists(self):
        normal1 = get_action_checklist("normal")
        normal2 = get_action_checklist("normal")
        assert normal1 == normal2
        assert len(normal1["items"]) >= 3
        assert normal1["footer"] == "Final decisions rest with authorised staff."

        watch = get_action_checklist("watch")
        elevated = get_action_checklist("elevated")
        assert len(watch["items"]) >= 3
        assert len(elevated["items"]) >= 3
        assert watch["items"] != normal1["items"]
        assert elevated["items"] != watch["items"]

    def test_invalid_tier_defaults_or_raises(self):
        with pytest.raises(ValueError, match="Unknown tier"):
            get_action_checklist("unknown_tier")


class TestExplanationNonCausalLanguageAT19:
    """AT-19: Explanation text is produced from stored numbers and contains no causal terms."""

    def test_explanation_text_uses_association_not_cause(self):
        text = format_explanation_text(
            horizon_weeks=1,
            top_feature_label="Admissions last week",
            top_feature_value=150.0,
            is_positive=True,
        )
        assert "associated with" in text
        text_lower = text.lower()
        for word in FORBIDDEN_CAUSAL_WORDS:
            assert word not in text_lower, f"Forbidden causal word '{word}' found in explanation text: {text}"
