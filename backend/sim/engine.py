import random
from collections import defaultdict

from sim.models import (
    EventKind,
    ResultType,
    SimEvent,
    SimGameInput,
    SimGameResult,
    SimGoalieStat,
    SimLine,
    SimSkaterStat,
    SimTeamLineup,
)
from sim.ratings import goalie_save_rating, line_offense, pair_defense
from sim.rotation import REGULATION_TICKS, defense_pair_at_tick, forward_line_at_tick

OT_MAX_TICKS = 5


def _shot_probability(off: float, deff: float) -> float:
    base = 0.35
    delta = (off - deff) / 200.0
    return max(0.05, min(0.7, base + delta))


def _save_probability(goalie: float, off: float) -> float:
    base = 0.90
    delta = (goalie - off) / 400.0
    return max(0.6, min(0.98, base + delta))


def _pick_weighted(rng: random.Random, items: list, weights: list[float]):
    total = sum(weights)
    r = rng.random() * total
    acc = 0.0
    for it, w in zip(items, weights):
        acc += w
        if r <= acc:
            return it
    return items[-1]


def _on_ice(team: SimTeamLineup, tick: int) -> tuple[SimLine, SimLine]:
    return (
        team.forward_lines[forward_line_at_tick(tick)],
        team.defense_pairs[defense_pair_at_tick(tick)],
    )


def _attempt(rng: random.Random, attackers: list, defenders_def: float, goalie):
    """Returns (kind|None, shooter_id, assists, goalie_id)."""
    off = sum(0.5 * s.shooting + 0.3 * s.passing + 0.2 * s.skating for s in attackers) / len(attackers)
    if rng.random() > _shot_probability(off, defenders_def):
        return (None, None, [], 0)
    shooter = _pick_weighted(rng, attackers, [s.shooting for s in attackers])
    if rng.random() < _save_probability(goalie_save_rating(goalie), shooter.shooting):
        return (EventKind.SAVE, shooter.id, [], goalie.id)
    others = [a for a in attackers if a.id != shooter.id]
    assist_count = rng.choices([0, 1, 2], weights=[15, 50, 35])[0]
    assists: list[int] = []
    pool = others[:]
    weights = [a.passing for a in pool]
    for _ in range(min(assist_count, len(pool))):
        a = _pick_weighted(rng, pool, weights)
        idx = pool.index(a)
        pool.pop(idx)
        weights.pop(idx)
        assists.append(a.id)
    return (EventKind.GOAL, shooter.id, assists, goalie.id)


def _run_tick(
    rng: random.Random,
    attacker_team: SimTeamLineup,
    defender_team: SimTeamLineup,
    tick: int,
    attacker_is_home: bool,
    events: list[SimEvent],
) -> int:
    fwd, _ = _on_ice(attacker_team, tick)
    _, dpair = _on_ice(defender_team, tick)
    attackers = list(fwd.skaters)
    kind, shooter_id, assists, goalie_id = _attempt(
        rng, attackers, pair_defense(dpair), defender_team.starting_goalie
    )
    if kind is None:
        return 0
    events.append(
        SimEvent(
            tick=tick,
            kind=kind,
            team_is_home=attacker_is_home,
            primary_skater_id=shooter_id,
            assist1_id=assists[0] if len(assists) >= 1 else None,
            assist2_id=assists[1] if len(assists) >= 2 else None,
            goalie_id=goalie_id,
        )
    )
    return 1 if kind == EventKind.GOAL else 0


def _simulate_phase(
    rng: random.Random,
    home: SimTeamLineup,
    away: SimTeamLineup,
    start_tick: int,
    end_tick: int,
    events: list[SimEvent],
    score: list[int],
    stop_on_goal: bool,
) -> None:
    for t in range(start_tick, end_tick):
        h_fwd, _ = _on_ice(home, t)
        a_fwd, _ = _on_ice(away, t)
        h_skating = sum(s.skating for s in h_fwd.skaters)
        a_skating = sum(s.skating for s in a_fwd.skaters)
        home_attacks = rng.random() < h_skating / (h_skating + a_skating)
        if home_attacks:
            score[0] += _run_tick(rng, home, away, t, True, events)
        else:
            score[1] += _run_tick(rng, away, home, t, False, events)
        if stop_on_goal and score[0] != score[1]:
            return


def simulate_game(input: SimGameInput) -> SimGameResult:
    rng = random.Random(input.seed)
    events: list[SimEvent] = []
    score = [0, 0]

    _simulate_phase(rng, input.home, input.away, 0, REGULATION_TICKS, events, score, stop_on_goal=False)
    result_type = ResultType.REG

    if score[0] == score[1]:
        _simulate_phase(
            rng,
            input.home,
            input.away,
            REGULATION_TICKS,
            REGULATION_TICKS + OT_MAX_TICKS,
            events,
            score,
            stop_on_goal=True,
        )
        if score[0] != score[1]:
            result_type = ResultType.OT
        else:
            home_strength = sum(line_offense(l) for l in input.home.forward_lines) - goalie_save_rating(
                input.away.starting_goalie
            )
            away_strength = sum(line_offense(l) for l in input.away.forward_lines) - goalie_save_rating(
                input.home.starting_goalie
            )
            offset = home_strength - away_strength
            home_wins = rng.random() < 0.5 + offset / 1000.0
            if home_wins:
                score[0] += 1
            else:
                score[1] += 1
            result_type = ResultType.SO

    skater_goals: dict[int, int] = defaultdict(int)
    skater_assists: dict[int, int] = defaultdict(int)
    skater_shots: dict[int, int] = defaultdict(int)
    goalie_sa: dict[int, int] = defaultdict(int)
    goalie_saves: dict[int, int] = defaultdict(int)
    goalie_ga: dict[int, int] = defaultdict(int)
    home_shots = away_shots = 0

    for e in events:
        if e.kind in (EventKind.SAVE, EventKind.GOAL):
            if e.primary_skater_id is not None:
                skater_shots[e.primary_skater_id] += 1
            if e.team_is_home:
                home_shots += 1
            else:
                away_shots += 1
        if e.kind == EventKind.SAVE and e.goalie_id is not None:
            goalie_sa[e.goalie_id] += 1
            goalie_saves[e.goalie_id] += 1
        if e.kind == EventKind.GOAL:
            if e.primary_skater_id is not None:
                skater_goals[e.primary_skater_id] += 1
            if e.assist1_id is not None:
                skater_assists[e.assist1_id] += 1
            if e.assist2_id is not None:
                skater_assists[e.assist2_id] += 1
            if e.goalie_id is not None:
                goalie_sa[e.goalie_id] += 1
                goalie_ga[e.goalie_id] += 1

    skater_ids = set(skater_goals) | set(skater_assists) | set(skater_shots)
    skater_stats = tuple(
        SimSkaterStat(
            skater_id=sid,
            goals=skater_goals[sid],
            assists=skater_assists[sid],
            shots=skater_shots[sid],
        )
        for sid in sorted(skater_ids)
    )
    goalie_ids = set(goalie_sa) | set(goalie_saves) | set(goalie_ga)
    goalie_stats = tuple(
        SimGoalieStat(
            goalie_id=gid,
            shots_against=goalie_sa[gid],
            saves=goalie_saves[gid],
            goals_against=goalie_ga[gid],
        )
        for gid in sorted(goalie_ids)
    )

    return SimGameResult(
        home_score=score[0],
        away_score=score[1],
        home_shots=home_shots,
        away_shots=away_shots,
        result_type=result_type,
        events=tuple(events),
        skater_stats=skater_stats,
        goalie_stats=goalie_stats,
    )
