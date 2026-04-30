"""Tunable simulation constants. Keep all gameplan-driven numbers here so
the engine stays declarative."""
from __future__ import annotations

GAMEPLAN_STYLE_MODIFIERS: dict[str, dict[str, float]] = {
    "balanced": {
        "shot_prob": 1.00, "opp_shot_prob": 1.00, "def_suppression": 1.00,
        "shot_quality_self": 0.00, "shot_quality_opp": 0.00,
        "self_penalty": 1.00, "opp_penalty": 1.00,
    },
    "offensive": {
        "shot_prob": 1.06, "opp_shot_prob": 1.00, "def_suppression": 0.97,
        "shot_quality_self": 0.05, "shot_quality_opp": 0.00,
        "self_penalty": 1.00, "opp_penalty": 1.00,
    },
    "defensive": {
        "shot_prob": 0.95, "opp_shot_prob": 0.95, "def_suppression": 1.00,
        "shot_quality_self": 0.00, "shot_quality_opp": -0.05,
        "self_penalty": 1.00, "opp_penalty": 1.00,
    },
    "physical": {
        "shot_prob": 1.00, "opp_shot_prob": 1.00, "def_suppression": 0.97,
        "shot_quality_self": 0.00, "shot_quality_opp": -0.05,
        "self_penalty": 1.35, "opp_penalty": 1.10,
    },
}

LINE_USAGE_FORWARD_DISTRIBUTION: dict[str, tuple[float, ...]] = {
    "balanced":       (0.40, 0.30, 0.20, 0.10),
    "ride_top_lines": (0.48, 0.32, 0.15, 0.05),
    "roll_all_lines": (0.30, 0.27, 0.23, 0.20),
}
LINE_USAGE_DEFENSE_DISTRIBUTION: dict[str, tuple[float, ...]] = {
    "balanced":       (0.45, 0.35, 0.20),
    "ride_top_lines": (0.52, 0.35, 0.13),
    "roll_all_lines": (0.38, 0.34, 0.28),
}

# Floor used after style shifts, so a quality bucket weight never goes
# negative or to zero.
SHOT_QUALITY_FLOOR: float = 0.02
