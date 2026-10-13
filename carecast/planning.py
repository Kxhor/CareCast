"""Pure planning functions for tiers, scenario analysis, and capacity illustration (Phase 4).

Features implemented:
- F5.2: Alert tier calculation (Normal, Watch, Elevated)
- F7.1: Scenario what-if scaling
- F8.2: Assumption-based steady-state capacity illustration (with reference_level = 0 handling)
- F9.1-F9.2: Action checklists by tier with mandatory non-clinical footer
- F6.3: Non-causal plain language explanation templates (AT-19)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from carecast.settings import load_toml

VALID_TIERS = {"normal", "watch", "elevated"}

# Causal verbs and terms explicitly prohibited by Rule G-0 and AT-19
FORBIDDEN_CAUSAL_WORDS = [
    "cause",
    "causes",
    "caused",
    "causing",
    "causal",
    "causality",
    "triggers",
    "triggered",
    "triggering",
    "leads to",
    "led to",
    "results in",
    "resulted in",
    "resulting in",
    "due to",
    "because of",
    "drives",
    "driven by",
    "produces",
    "produced",
]

DEFAULT_ACTIONS: dict[str, list[str]] = {
    "normal": [
        "Maintain routine infection-control surveillance and standard bed tracking.",
        "Review weekly admission trajectory and regional community transmission reports.",
        "Verify baseline respiratory medication and personal protective equipment supplies.",
    ],
    "watch": [
        "Review projected discharge schedule and expedite weekend bed turnover.",
        "Audit on-call clinical nurse roster and evaluate cross-department staffing support.",
        "Assess step-down and intermediate-care bed flexibility for potential surge intake.",
        "Monitor daily emergency department respiratory visit rates for inflection points.",
    ],
    "elevated": [
        "Convene clinical leadership and activate respiratory surge response protocol.",
        "Evaluate temporary deferral of non-urgent elective surgical admissions.",
        "Mobilize supplemental nursing and respiratory therapy shifts from staffing pool.",
        "Establish daily coordination with regional transfer centers and hospital network.",
    ],
}

DEFAULT_ACTIONS_FOOTER = "Final decisions rest with authorised staff."


def load_planning_config(config_path: Path | str = "config/planning.toml") -> dict[str, Any]:
    """Load the planning configuration TOML file."""
    path = Path(config_path)
    if not path.exists():
        return {}
    return load_toml(path)


def calculate_tier(point: float, lower: float, upper: float, threshold: float) -> str:
    """Evaluate early warning alert tier per PRD F5.2.
    
    Tiers:
      - 'elevated' if point > threshold
      - 'watch' if point <= threshold < upper
      - 'normal' if upper <= threshold
    """
    if point > threshold:
        return "elevated"
    if threshold < upper:
        return "watch"
    return "normal"


def calculate_scenario(
    base_point: float,
    base_lower: float,
    base_upper: float,
    surge_pct: float,
) -> dict[str, float]:
    """Calculate scaled forecast values for what-if scenario (PRD F7.1 / AT-21).
    
    adjusted = base * (1 + surge_pct / 100) for point, lower, upper.
    All outputs are clamped to non-negative floats.
    """
    factor = 1.0 + (surge_pct / 100.0)
    return {
        "point": max(0.0, float(base_point * factor)),
        "lower": max(0.0, float(base_lower * factor)),
        "upper": max(0.0, float(base_upper * factor)),
    }


def calculate_capacity_illustration(
    scenario_point: float,
    reference_level: float,
    typical_weekly_admissions: float,
    alos_days: float,
    staffed_beds: float,
    patients_per_nurse: float,
) -> dict[str, Any]:
    """Calculate steady-state capacity metrics per PRD F8.2.
    
    Formulae (Little's law approximation):
      - relative_change = scenario_point / reference_level
      - hospital_weekly_admissions = typical_weekly_admissions * relative_change
      - est_occupied_beds = hospital_weekly_admissions * alos_days / 7
      - bed_gap = est_occupied_beds - staffed_beds
      - nurses_per_shift = est_occupied_beds / patients_per_nurse
      
    If reference_level is zero or non-positive, capacity metrics are set to None
    and an explanatory message is returned.
    """
    if reference_level <= 0:
        return {
            "relative_change": None,
            "hospital_weekly_admissions": None,
            "est_occupied_beds": None,
            "bed_gap": None,
            "nurses_per_shift": None,
            "message": "Reference level is zero; capacity metrics cannot be calculated.",
        }

    relative_change = float(scenario_point / reference_level)
    hospital_weekly_admissions = float(typical_weekly_admissions * relative_change)
    est_occupied_beds = float(hospital_weekly_admissions * alos_days / 7.0)
    bed_gap = float(est_occupied_beds - staffed_beds)
    nurses_per_shift = float(est_occupied_beds / patients_per_nurse)

    return {
        "relative_change": relative_change,
        "hospital_weekly_admissions": hospital_weekly_admissions,
        "est_occupied_beds": est_occupied_beds,
        "bed_gap": bed_gap,
        "nurses_per_shift": nurses_per_shift,
        "message": None,
    }


def get_action_checklist(
    tier: str,
    actions_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Retrieve the static checklist for the specified tier per PRD F9.1-F9.2."""
    tier_clean = tier.lower().strip()
    if tier_clean not in VALID_TIERS:
        raise ValueError(f"Unknown tier '{tier}'. Must be one of: {sorted(VALID_TIERS)}")

    items: list[str] = []
    footer: str = DEFAULT_ACTIONS_FOOTER

    if actions_config:
        tier_data = actions_config.get(tier_clean)
        if isinstance(tier_data, dict) and "items" in tier_data:
            items = list(tier_data["items"])
        elif isinstance(tier_data, list):
            items = list(tier_data)
        if "footer" in actions_config and isinstance(actions_config["footer"], str):
            footer = actions_config["footer"]

    if not items:
        items = list(DEFAULT_ACTIONS[tier_clean])

    return {
        "tier": tier_clean,
        "items": items,
        "footer": footer,
    }


def format_explanation_text(
    horizon_weeks: int,
    top_feature_label: str,
    top_feature_value: float,
    is_positive: bool,
) -> str:
    """Format plain-language explanation text adhering strictly to non-causal language (AT-19)."""
    direction = "positive" if is_positive else "negative"
    return (
        f"The largest {direction} contribution to the {horizon_weeks}-week forecast is "
        f"associated with {top_feature_label.lower()}."
    )
