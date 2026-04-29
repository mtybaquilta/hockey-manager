"""Pure player development module.

No FastAPI, no SQLAlchemy. Deterministic given inputs and seed.

The orchestrator pre-computes ``perf_signal`` (league-relative performance,
clamped to [-1, 1]) so this module never touches the database.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal

PlayerType = Literal["skater", "goalie"]
SummaryReason = Literal["growth", "decline", "boom", "bust", "plateau", "mixed"]
EventReason = Literal["growth", "decline", "boom", "bust"]
DevType = Literal["steady", "early_bloomer", "late_bloomer", "boom_or_bust"]

SKATER_ATTRIBUTES = ("skating", "shooting", "passing", "defense", "physical")
GOALIE_ATTRIBUTES = ("reflexes", "positioning", "rebound_control", "puck_handling", "mental")

ATTR_MIN = 20
ATTR_MAX = 100


@dataclass(frozen=True)
class PlayerDevInput:
    player_id: int
    player_type: PlayerType
    age: int
    attrs: dict[str, int]
    potential: int
    development_type: DevType
    perf_signal: float  # clamped [-1, 1]


@dataclass(frozen=True)
class DevEvent:
    attribute: str
    old_value: int
    new_value: int
    delta: int
    reason: EventReason


@dataclass(frozen=True)
class PlayerDevResult:
    new_attrs: dict[str, int]
    events: tuple[DevEvent, ...]
    summary_reason: SummaryReason
    overall_before: int
    overall_after: int


def _attribute_set(player_type: PlayerType) -> tuple[str, ...]:
    return SKATER_ATTRIBUTES if player_type == "skater" else GOALIE_ATTRIBUTES


def overall_from_attrs(player: PlayerDevInput) -> int:
    attrs = _attribute_set(player.player_type)
    return round(sum(player.attrs[a] for a in attrs) / len(attrs))


def _overall_from_dict(player_type: PlayerType, attrs: dict[str, int]) -> int:
    keys = _attribute_set(player_type)
    return round(sum(attrs[a] for a in keys) / len(keys))


# Probability tables (p_grow, p_decline) per (player_type, age_bucket).
# Buckets are inclusive ranges; first match wins.
_SKATER_AGE_TABLE = (
    ((18, 22), (0.55, 0.00)),
    ((23, 26), (0.30, 0.02)),
    ((27, 31), (0.10, 0.05)),
    ((32, 34), (0.03, 0.25)),
    ((35, 99), (0.01, 0.45)),
)
_GOALIE_AGE_TABLE = (
    ((18, 24), (0.55, 0.00)),
    ((25, 28), (0.30, 0.02)),
    ((29, 33), (0.10, 0.05)),
    ((34, 36), (0.03, 0.25)),
    ((37, 99), (0.01, 0.45)),
)


def _age_probabilities(player_type: PlayerType, age: int) -> tuple[float, float]:
    table = _SKATER_AGE_TABLE if player_type == "skater" else _GOALIE_AGE_TABLE
    for (lo, hi), probs in table:
        if lo <= age <= hi:
            return probs
    return (0.0, 0.5)


def _apply_dev_type(
    p_grow: float, p_decline: float, age: int, dev_type: DevType
) -> tuple[float, float]:
    if dev_type == "early_bloomer":
        if 18 <= age <= 23:
            p_grow *= 1.3
        if age >= 27:
            p_grow *= 0.6
    elif dev_type == "late_bloomer":
        if 18 <= age <= 23:
            p_grow *= 0.6
        if 24 <= age <= 29:
            p_grow *= 1.3
    return p_grow, p_decline


def _potential_gap_modifier(p_grow: float, gap: int) -> float:
    if gap <= 0:
        return p_grow * 0.15
    return p_grow * max(0.2, min(1.5, 0.2 + gap / 15))


def _perf_modifier(p_grow: float, p_decline: float, s: float) -> tuple[float, float]:
    return (p_grow * (1 + 0.15 * s), p_decline * (1 - 0.15 * s))


def _grow_magnitude(rng: random.Random, dev_type: DevType) -> int:
    if dev_type == "boom_or_bust":
        if rng.random() < 0.05:
            return 3
        if rng.random() < 0.50:
            return 2
        return 1
    return 2 if rng.random() < 0.25 else 1


def _decline_magnitude(rng: random.Random, dev_type: DevType) -> int:
    if dev_type == "boom_or_bust" and rng.random() < 0.30:
        return 2
    return 1


def _clamp_attr(v: int) -> int:
    return max(ATTR_MIN, min(ATTR_MAX, v))


def classify_summary(events: tuple[DevEvent, ...], dev_type: DevType) -> SummaryReason:
    if not events:
        return "plateau"
    deltas = [e.delta for e in events]
    grew = [d for d in deltas if d > 0]
    declined = [d for d in deltas if d < 0]
    if grew and not declined and dev_type == "boom_or_bust" and any(d >= 2 for d in grew):
        return "boom"
    if declined and not grew and dev_type == "boom_or_bust" and any(d <= -2 for d in declined):
        return "bust"
    if grew and declined:
        return "mixed"
    total = sum(deltas)
    if total > 0:
        return "growth"
    if total < 0:
        return "decline"
    return "plateau"


def develop_player(player: PlayerDevInput, season_seed: int) -> PlayerDevResult:
    rng = random.Random(hash((season_seed, player.player_type, player.player_id)) & 0x7FFFFFFF)
    overall_before = overall_from_attrs(player)
    new_attrs = dict(player.attrs)
    events: list[DevEvent] = []

    base_grow, base_decline = _age_probabilities(player.player_type, player.age)
    base_grow, base_decline = _apply_dev_type(
        base_grow, base_decline, player.age, player.development_type
    )

    for attr in _attribute_set(player.player_type):
        old = new_attrs[attr]
        current_overall = _overall_from_dict(player.player_type, new_attrs)
        gap = player.potential - current_overall
        p_grow = _potential_gap_modifier(base_grow, gap)
        p_grow, p_decline = _perf_modifier(p_grow, base_decline, player.perf_signal)
        p_grow = max(0.0, min(0.95, p_grow))
        p_decline = max(0.0, min(0.95, p_decline))
        if p_grow + p_decline > 0.99:
            scale = 0.99 / (p_grow + p_decline)
            p_grow *= scale
            p_decline *= scale

        r = rng.random()
        if r < p_grow:
            mag = _grow_magnitude(rng, player.development_type)
            new = _clamp_attr(old + mag)
            if new != old:
                events.append(DevEvent(attr, old, new, new - old, "growth"))
                new_attrs[attr] = new
        elif r > 1 - p_decline:
            mag = _decline_magnitude(rng, player.development_type)
            new = _clamp_attr(old - mag)
            if new != old:
                events.append(DevEvent(attr, old, new, new - old, "decline"))
                new_attrs[attr] = new

    summary = classify_summary(tuple(events), player.development_type)
    if summary in ("boom", "bust"):
        target_reason: EventReason = "boom" if summary == "boom" else "bust"
        events = [
            DevEvent(e.attribute, e.old_value, e.new_value, e.delta, target_reason)
            for e in events
        ]

    overall_after = _overall_from_dict(player.player_type, new_attrs)

    return PlayerDevResult(
        new_attrs=new_attrs,
        events=tuple(events),
        summary_reason=summary,
        overall_before=overall_before,
        overall_after=overall_after,
    )
