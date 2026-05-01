"""Procedural team builder used by sim tools.

Mirrors the attribute distributions in `app/services/generation/players.py` so
the balance report reflects what regular-season games actually look like.
Lives outside `tests/` so the script can run without a test runner and
without importing the FastAPI / SQLAlchemy layers.
"""
import random

from sim.models import Position, SimGoalie, SimLine, SimSkater, SimTeamLineup

# Mirrors app.services.generation.players.SKATER_LAYOUT.
SKATER_LAYOUT: tuple[Position, ...] = (
    Position.LW, Position.LW, Position.LW, Position.LW,
    Position.C, Position.C, Position.C, Position.C,
    Position.RW, Position.RW, Position.RW, Position.RW,
    Position.LD, Position.LD, Position.LD,
    Position.RD, Position.RD, Position.RD,
)


def _attr(rng: random.Random) -> int:
    """Same distribution as the real player generator: gauss(70, 8) clamped."""
    return max(40, min(95, int(rng.gauss(70, 8))))


def _goalie_attr(rng: random.Random) -> int:
    """Mirrors generation/players.py:_goalie_attr — goalies skew higher than skaters."""
    return max(45, min(95, int(rng.gauss(75, 6))))


def _build_skater(rng: random.Random, skater_id: int, position: Position) -> SimSkater:
    is_def = position in (Position.LD, Position.RD)
    defense = _attr(rng) if is_def else max(40, _attr(rng) - 5)
    return SimSkater(
        id=skater_id,
        position=position,
        skating=_attr(rng),
        shooting=_attr(rng),
        passing=_attr(rng),
        defense=defense,
        physical=_attr(rng),
    )


def _build_goalie(rng: random.Random, goalie_id: int) -> SimGoalie:
    return SimGoalie(
        id=goalie_id,
        reflexes=_goalie_attr(rng),
        positioning=_goalie_attr(rng),
        rebound_control=_goalie_attr(rng),
        puck_handling=_goalie_attr(rng),
        mental=_goalie_attr(rng),
    )


def _overall(s: SimSkater) -> int:
    return s.skating + s.shooting + s.passing + s.defense + s.physical


def procedural_team(rng: random.Random, id_base: int) -> SimTeamLineup:
    """Build a synthetic team whose lines mirror the real lineup builder.

    `app/services/generation/lineups.py` sorts each position by overall
    (skating+shooting+passing+defense+physical) and assigns the best LW/C/RW
    to line 1, second-best to line 2, etc. The report's synthetic team must
    do the same; otherwise top-scorer concentration is wildly under-reported
    because line 1 ends up no better than line 4.
    """
    skaters = [_build_skater(rng, id_base + i, pos) for i, pos in enumerate(SKATER_LAYOUT)]
    by_pos: dict[Position, list[SimSkater]] = {p: [] for p in Position}
    for s in skaters:
        by_pos[s.position].append(s)
    for p in by_pos:
        by_pos[p].sort(key=lambda s: -_overall(s))

    forward_lines = tuple(
        SimLine(skaters=(by_pos[Position.LW][i], by_pos[Position.C][i], by_pos[Position.RW][i]))
        for i in range(4)
    )
    pairs = tuple(
        SimLine(skaters=(by_pos[Position.LD][i], by_pos[Position.RD][i]))
        for i in range(3)
    )
    goalie = _build_goalie(rng, id_base + 200)
    return SimTeamLineup(forward_lines=forward_lines, defense_pairs=pairs, starting_goalie=goalie)
