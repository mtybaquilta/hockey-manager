"""Auto-selected power play and penalty kill units.

Picked once per (team, game) from the existing lineup. No UI; no input from
the user. Selection is purely a function of the lineup's skater attributes,
so identical inputs always produce identical units.

A PP unit is 3F + 2D, biased toward shooting / passing / skating.
A PK unit is 2F + 2D, biased toward defense / skating / physical.
"""
from dataclasses import dataclass

from sim.models import Position, SimSkater, SimTeamLineup


def pp_score(s: SimSkater) -> float:
    return 0.45 * s.shooting + 0.35 * s.passing + 0.2 * s.skating


def pk_score(s: SimSkater) -> float:
    return 0.45 * s.defense + 0.3 * s.skating + 0.25 * s.physical


_FORWARD_POSITIONS = {Position.LW, Position.C, Position.RW}
_DEFENSE_POSITIONS = {Position.LD, Position.RD}


def _all_skaters(team: SimTeamLineup) -> list[SimSkater]:
    skaters: list[SimSkater] = []
    for line in team.forward_lines:
        skaters.extend(line.skaters)
    for pair in team.defense_pairs:
        skaters.extend(pair.skaters)
    return skaters


def _split_by_role(skaters: list[SimSkater]) -> tuple[list[SimSkater], list[SimSkater]]:
    forwards = [s for s in skaters if s.position in _FORWARD_POSITIONS]
    defense = [s for s in skaters if s.position in _DEFENSE_POSITIONS]
    return forwards, defense


def _top_n(skaters: list[SimSkater], score_fn, n: int) -> tuple[SimSkater, ...]:
    # Tie-breaking on id keeps selection deterministic across runs.
    return tuple(sorted(skaters, key=lambda s: (-score_fn(s), s.id))[:n])


@dataclass(frozen=True)
class SpecialTeams:
    pp_forwards: tuple[SimSkater, SimSkater, SimSkater]
    pp_defense: tuple[SimSkater, SimSkater]
    pk_forwards: tuple[SimSkater, SimSkater]
    pk_defense: tuple[SimSkater, SimSkater]


def select_special_teams(team: SimTeamLineup) -> SpecialTeams:
    forwards, defense = _split_by_role(_all_skaters(team))
    pp_f = _top_n(forwards, pp_score, 3)
    pp_d = _top_n(defense, pp_score, 2)
    pk_f = _top_n(forwards, pk_score, 2)
    pk_d = _top_n(defense, pk_score, 2)
    return SpecialTeams(
        pp_forwards=(pp_f[0], pp_f[1], pp_f[2]),
        pp_defense=(pp_d[0], pp_d[1]),
        pk_forwards=(pk_f[0], pk_f[1]),
        pk_defense=(pk_d[0], pk_d[1]),
    )


def pp_unit_offense(st: SpecialTeams) -> float:
    skaters = (*st.pp_forwards, *st.pp_defense)
    return sum(0.5 * s.shooting + 0.3 * s.passing + 0.2 * s.skating for s in skaters) / len(skaters)


def pk_unit_defense(st: SpecialTeams) -> float:
    skaters = (*st.pk_forwards, *st.pk_defense)
    return sum(0.5 * s.defense + 0.3 * s.skating + 0.2 * s.physical for s in skaters) / len(skaters)
