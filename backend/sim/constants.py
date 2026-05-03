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
        "shot_prob": 1.02, "opp_shot_prob": 1.01, "def_suppression": 0.99,
        "shot_quality_self": 0.02, "shot_quality_opp": 0.01,
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
    "balanced":       (0.37, 0.29, 0.22, 0.12),
    "ride_top_lines": (0.41, 0.30, 0.19, 0.10),
    "roll_all_lines": (0.31, 0.27, 0.23, 0.19),
}
LINE_USAGE_DEFENSE_DISTRIBUTION: dict[str, tuple[float, ...]] = {
    "balanced":       (0.42, 0.34, 0.24),
    "ride_top_lines": (0.46, 0.34, 0.20),
    "roll_all_lines": (0.37, 0.34, 0.29),
}

# Floor used after style shifts, so a quality bucket weight never goes
# negative or to zero.
SHOT_QUALITY_FLOOR: float = 0.02
