"""Deterministic, period-aware game simulation.

Tick model
----------
A regulation game is REGULATION_TICKS = 180 ticks split into 3 equal periods.
Each tick represents roughly 20 seconds of play and produces at most one shot
attempt. Overtime adds up to OT_MAX_TICKS more ticks; ties after that go to a
shootout decided by team strength.

Strength model
--------------
At every tick we look at active penalties on each team and classify the
attacker as EV / PP / SH. PP boosts shot probability and slightly suppresses
saves; SH does the opposite. Penalties are 4-tick minor (~2 minutes) and end
early if the opposing team scores while the offender is in the box.
"""
import random
from collections import defaultdict
from dataclasses import dataclass

from sim.constants import (
    GAMEPLAN_STYLE_MODIFIERS,
    LINE_USAGE_DEFENSE_DISTRIBUTION,
    LINE_USAGE_FORWARD_DISTRIBUTION,
    SHOT_QUALITY_FLOOR,
)
from sim.models import (
    EventKind,
    ResultType,
    ShotQuality,
    SimEvent,
    SimGameInput,
    SimGameplan,
    SimGameResult,
    SimGoalieStat,
    SimLine,
    SimSkaterStat,
    SimTeamInput,
    SimTeamLineup,
    Strength,
)
from sim.ratings import goalie_form_offset, goalie_save_rating, line_offense, pair_defense
from sim.rotation import REGULATION_TICKS, build_rotation_schedule, period_at_tick
from sim.special_teams import (
    SpecialTeams,
    pk_unit_defense,
    pp_defense_for,
    pp_forwards_for,
    pp_unit_offense,
    select_special_teams,
)

OT_MAX_TICKS = 25
PENALTY_DURATION_TICKS = 4
PENALTY_PER_TICK_PROB = 0.018

# Tiny home-ice possession edge applied to attacker selection.
HOME_POSSESSION_BIAS = 1.04

# Strength multipliers applied to base shot probability.
SHOT_PROB_PP = 1.7
SHOT_PROB_SH = 0.5
# Multiplier applied to base save probability when shooter is on the PP.
SAVE_PROB_VS_PP = 0.88

# Per-bucket save-probability multipliers. A HIGH-quality shot is harder to stop.
SAVE_MULT_BY_QUALITY: dict[ShotQuality, float] = {
    ShotQuality.LOW: 1.04,
    ShotQuality.MEDIUM: 1.0,
    ShotQuality.HIGH: 0.92,
}

# Base bucket weights at neutral conditions; biased by attacker/defender margin and strength.
_BASE_QUALITY_WEIGHTS: dict[ShotQuality, float] = {
    ShotQuality.LOW: 0.35,
    ShotQuality.MEDIUM: 0.45,
    ShotQuality.HIGH: 0.20,
}


@dataclass
class _PenaltyClock:
    """Active penalties for one team, oldest first."""

    remaining: list[int]  # ticks left, parallel to skater_ids
    skater_ids: list[int]

    def shorthanded(self) -> bool:
        return bool(self.remaining)

    def tick_down(self) -> None:
        keep_r, keep_s = [], []
        for r, sid in zip(self.remaining, self.skater_ids):
            if r > 1:
                keep_r.append(r - 1)
                keep_s.append(sid)
        self.remaining, self.skater_ids = keep_r, keep_s

    def release_oldest(self) -> None:
        if self.remaining:
            self.remaining.pop(0)
            self.skater_ids.pop(0)

    def add(self, skater_id: int) -> None:
        self.remaining.append(PENALTY_DURATION_TICKS)
        self.skater_ids.append(skater_id)


def _shot_probability(off: float, deff: float) -> float:
    base = 0.35
    delta = (off - deff) / 200.0
    return max(0.05, min(0.7, base + delta))


def _save_probability(goalie_rating: float, shooter_shooting: int) -> float:
    base = 0.905
    delta = (goalie_rating - shooter_shooting) / 400.0
    return max(0.6, min(0.96, base + delta))


def _strength_for(attacker_box: _PenaltyClock, defender_box: _PenaltyClock) -> Strength:
    if attacker_box.shorthanded() and not defender_box.shorthanded():
        return Strength.SH
    if defender_box.shorthanded() and not attacker_box.shorthanded():
        return Strength.PP
    return Strength.EV


def _style_mod(gp: SimGameplan, key: str) -> float:
    return GAMEPLAN_STYLE_MODIFIERS[gp.style][key]


def _on_ice_with_schedule(
    team: SimTeamLineup,
    fwd_sched: tuple[int, ...],
    def_sched: tuple[int, ...],
    tick: int,
) -> tuple[SimLine, SimLine]:
    ft = tick % len(fwd_sched) if fwd_sched else 0
    dt = tick % len(def_sched) if def_sched else 0
    return team.forward_lines[fwd_sched[ft]], team.defense_pairs[def_sched[dt]]


def _shooter_weight(s) -> float:
    """Selection weight for who takes a shot from the on-ice attackers.

    Linear in `shooting` is too top-heavy: a 90-rated forward on a line of
    70-rated linemates ends up with ~600 shots over an 82-game sample. We
    flatten with a large baseline so elite shooters still lead, but a star
    on line 1 + PP doesn't dominate the team's shot diet.
    """
    return 100.0 + s.shooting


def _pick_weighted(rng: random.Random, items: list, weights: list[float]):
    total = sum(weights)
    r = rng.random() * total
    acc = 0.0
    for it, w in zip(items, weights):
        acc += w
        if r <= acc:
            return it
    return items[-1]


def _maybe_penalty(
    rng: random.Random,
    attackers: list,
    defenders: list,
    attacker_box: _PenaltyClock,
    defender_box: _PenaltyClock,
    attacker_gp: SimGameplan,
    defender_gp: SimGameplan,
) -> tuple[bool, int | None]:
    """Roll for a penalty against any on-ice skater. Returns (is_attacker_penalty, skater_id)."""
    avg_mod = (
        _style_mod(attacker_gp, "self_penalty")
        + _style_mod(defender_gp, "opp_penalty")
    ) / 2.0
    if rng.random() >= PENALTY_PER_TICK_PROB * avg_mod:
        return (False, None)
    # Penalize someone on the more physical line; player picked weighted by physical.
    pool = attackers + defenders
    weights = [s.physical for s in pool]
    offender = _pick_weighted(rng, pool, weights)
    is_attacker = offender in attackers
    box = attacker_box if is_attacker else defender_box
    box.add(offender.id)
    return (is_attacker, offender.id)


def _classify_shot_quality(
    rng: random.Random,
    off: float,
    deff: float,
    strength: Strength,
    attacker_gp: SimGameplan,
    defender_gp: SimGameplan,
) -> ShotQuality:
    """Pick a quality bucket. Better attacker margin shifts weight to HIGH; PP also
    shifts toward HIGH; SH shifts toward LOW. Deterministic given rng + inputs."""
    margin = (off - deff) / 30.0  # ~ -1..+1 typical range
    weights = {
        ShotQuality.LOW: max(0.05, _BASE_QUALITY_WEIGHTS[ShotQuality.LOW] - 0.10 * margin),
        ShotQuality.MEDIUM: _BASE_QUALITY_WEIGHTS[ShotQuality.MEDIUM],
        ShotQuality.HIGH: max(0.05, _BASE_QUALITY_WEIGHTS[ShotQuality.HIGH] + 0.10 * margin),
    }
    if strength == Strength.PP:
        weights[ShotQuality.HIGH] += 0.15
        weights[ShotQuality.LOW] = max(0.05, weights[ShotQuality.LOW] - 0.10)
    elif strength == Strength.SH:
        weights[ShotQuality.LOW] += 0.15
        weights[ShotQuality.HIGH] = max(0.02, weights[ShotQuality.HIGH] - 0.10)

    # Style tilt: positive value pushes toward HIGH; negative pushes toward LOW.
    tilt = (
        _style_mod(attacker_gp, "shot_quality_self")
        - _style_mod(defender_gp, "shot_quality_opp")
    )
    weights[ShotQuality.HIGH] = max(SHOT_QUALITY_FLOOR, weights[ShotQuality.HIGH] + tilt)
    weights[ShotQuality.LOW] = max(SHOT_QUALITY_FLOOR, weights[ShotQuality.LOW] - tilt)

    buckets = list(weights.keys())
    return rng.choices(buckets, weights=[weights[b] for b in buckets])[0]


def _attempt_shot(
    rng: random.Random,
    attackers: list,
    defender_def: float,
    defender_goalie,
    goalie_form: float,
    strength: Strength,
    attacker_gp: SimGameplan,
    defender_gp: SimGameplan,
) -> tuple[EventKind | None, int | None, list[int], int, ShotQuality | None]:
    """Returns (kind|None, shooter_id, assists, goalie_id, shot_quality)."""
    off = sum(0.5 * s.shooting + 0.3 * s.passing + 0.2 * s.skating for s in attackers) / len(attackers)
    shot_prob = _shot_probability(off, defender_def)
    if strength == Strength.PP:
        shot_prob *= SHOT_PROB_PP
    elif strength == Strength.SH:
        shot_prob *= SHOT_PROB_SH
    shot_prob *= _style_mod(attacker_gp, "shot_prob") * _style_mod(defender_gp, "opp_shot_prob")
    if rng.random() > shot_prob:
        return (None, None, [], 0, None)

    shooter = _pick_weighted(rng, attackers, [_shooter_weight(s) for s in attackers])
    quality = _classify_shot_quality(rng, off, defender_def, strength, attacker_gp, defender_gp)
    save_prob = _save_probability(goalie_save_rating(defender_goalie) + goalie_form, shooter.shooting)
    save_prob *= SAVE_MULT_BY_QUALITY[quality]
    if strength == Strength.PP:
        save_prob *= SAVE_PROB_VS_PP
    save_prob = max(0.4, min(0.97, save_prob))
    if rng.random() < save_prob:
        return (EventKind.SAVE, shooter.id, [], defender_goalie.id, quality)

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
    return (EventKind.GOAL, shooter.id, assists, defender_goalie.id, quality)


def _on_ice_attackers_and_def(
    attacker_team: SimTeamInput,
    defender_team: SimTeamInput,
    attacker_st: SpecialTeams,
    defender_st: SpecialTeams,
    strength: Strength,
    tick: int,
    attacker_fwd_sched: tuple[int, ...],
    attacker_def_sched: tuple[int, ...],
    defender_fwd_sched: tuple[int, ...],
    defender_def_sched: tuple[int, ...],
) -> tuple[list, list, float]:
    """Pick on-ice attacking forwards, on-ice defending skaters (for penalty draws),
    and the defender's defensive rating used for shot-probability.

    Even strength: rotating forward line vs rotating defense pair.
    Power play: PP forwards vs PK defenders. Better forwards, worse defenders.
    Shorthanded: PK forwards vs PP defenders. Fewer/weaker shooters, lighter defense.

    Defensive suppression from the defender's gameplan style is applied here
    exactly once on the returned `deff` value.
    """
    if strength == Strength.PP:
        attackers = list(pp_forwards_for(attacker_st, tick))
        defenders = list(defender_st.pk_defense)
        deff = pk_unit_defense(defender_st)
    elif strength == Strength.SH:
        attackers = list(attacker_st.pk_forwards)
        opp_pp_d = pp_defense_for(defender_st, tick)
        defenders = list(opp_pp_d)
        deff = pair_defense(SimLine(skaters=opp_pp_d))
    else:
        fwd, _ = _on_ice_with_schedule(
            attacker_team.lineup, attacker_fwd_sched, attacker_def_sched, tick
        )
        _, def_pair = _on_ice_with_schedule(
            defender_team.lineup, defender_fwd_sched, defender_def_sched, tick
        )
        attackers = list(fwd.skaters)
        defenders = list(def_pair.skaters)
        deff = pair_defense(def_pair)
    deff *= _style_mod(defender_team.gameplan, "def_suppression")
    return attackers, defenders, deff


def _run_tick(
    rng: random.Random,
    attacker: SimTeamInput,
    defender: SimTeamInput,
    attacker_st: SpecialTeams,
    defender_st: SpecialTeams,
    attacker_is_home: bool,
    attacker_box: _PenaltyClock,
    defender_box: _PenaltyClock,
    goalie_forms: dict[int, float],
    tick: int,
    events: list[SimEvent],
    home_fwd_sched: tuple[int, ...],
    home_def_sched: tuple[int, ...],
    away_fwd_sched: tuple[int, ...],
    away_def_sched: tuple[int, ...],
) -> int:
    """Run a single attacking tick. Returns goals scored by attacker (0 or 1)."""
    period = period_at_tick(tick)
    strength = _strength_for(attacker_box, defender_box)
    if attacker_is_home:
        a_fwd, a_def = home_fwd_sched, home_def_sched
        d_fwd, d_def = away_fwd_sched, away_def_sched
    else:
        a_fwd, a_def = away_fwd_sched, away_def_sched
        d_fwd, d_def = home_fwd_sched, home_def_sched
    attackers, defenders, deff = _on_ice_attackers_and_def(
        attacker, defender, attacker_st, defender_st, strength, tick,
        a_fwd, a_def, d_fwd, d_def,
    )

    # Penalty roll first; a penalty consumes the tick (no shot) for simplicity.
    is_attacker_pen, offender_id = _maybe_penalty(
        rng, attackers, defenders, attacker_box, defender_box,
        attacker.gameplan, defender.gameplan,
    )
    if offender_id is not None:
        team_is_home = attacker_is_home if is_attacker_pen else (not attacker_is_home)
        events.append(
            SimEvent(
                tick=tick,
                period=period,
                kind=EventKind.PENALTY,
                team_is_home=team_is_home,
                strength=None,
                primary_skater_id=offender_id,
                assist1_id=None,
                assist2_id=None,
                goalie_id=None,
                penalty_duration_ticks=PENALTY_DURATION_TICKS,
            )
        )
        return 0

    kind, shooter_id, assists, goalie_id, quality = _attempt_shot(
        rng,
        attackers,
        deff,
        defender.lineup.starting_goalie,
        goalie_forms[defender.lineup.starting_goalie.id],
        strength,
        attacker.gameplan,
        defender.gameplan,
    )
    if kind is None:
        return 0

    events.append(
        SimEvent(
            tick=tick,
            period=period,
            kind=kind,
            team_is_home=attacker_is_home,
            strength=strength,
            primary_skater_id=shooter_id,
            assist1_id=assists[0] if len(assists) >= 1 else None,
            assist2_id=assists[1] if len(assists) >= 2 else None,
            goalie_id=goalie_id,
            shot_quality=quality,
        )
    )
    return 1 if kind == EventKind.GOAL else 0


def _simulate_phase(
    rng: random.Random,
    home: SimTeamInput,
    away: SimTeamInput,
    home_st: SpecialTeams,
    away_st: SpecialTeams,
    home_box: _PenaltyClock,
    away_box: _PenaltyClock,
    goalie_forms: dict[int, float],
    start_tick: int,
    end_tick: int,
    events: list[SimEvent],
    score: list[int],
    stop_on_goal: bool,
    home_fwd_sched: tuple[int, ...],
    home_def_sched: tuple[int, ...],
    away_fwd_sched: tuple[int, ...],
    away_def_sched: tuple[int, ...],
) -> None:
    for t in range(start_tick, end_tick):
        # Possession weighted by on-ice forward skating; PP team gets a possession edge.
        h_fwd_idx = home_fwd_sched[t % len(home_fwd_sched)]
        a_fwd_idx = away_fwd_sched[t % len(away_fwd_sched)]
        h_fwd = home.lineup.forward_lines[h_fwd_idx]
        a_fwd = away.lineup.forward_lines[a_fwd_idx]
        h_weight = sum(s.skating for s in h_fwd.skaters) * HOME_POSSESSION_BIAS
        a_weight = sum(s.skating for s in a_fwd.skaters)
        if home_box.shorthanded() and not away_box.shorthanded():
            a_weight *= 1.5
        elif away_box.shorthanded() and not home_box.shorthanded():
            h_weight *= 1.5
        home_attacks = rng.random() < h_weight / (h_weight + a_weight)

        if home_attacks:
            scored = _run_tick(
                rng, home, away, home_st, away_st, True,
                home_box, away_box, goalie_forms, t, events,
                home_fwd_sched, home_def_sched, away_fwd_sched, away_def_sched,
            )
            score[0] += scored
            if scored and away_box.shorthanded():
                away_box.release_oldest()
        else:
            scored = _run_tick(
                rng, away, home, away_st, home_st, False,
                away_box, home_box, goalie_forms, t, events,
                home_fwd_sched, home_def_sched, away_fwd_sched, away_def_sched,
            )
            score[1] += scored
            if scored and home_box.shorthanded():
                home_box.release_oldest()

        home_box.tick_down()
        away_box.tick_down()

        if stop_on_goal and score[0] != score[1]:
            return


def _aggregate_stats(
    events: tuple[SimEvent, ...],
) -> tuple[
    tuple[SimSkaterStat, ...],
    tuple[SimGoalieStat, ...],
    int,
    int,
    tuple[int, int, int, int],
    tuple[int, int, int, int],
    tuple[int, int, int, int],
    tuple[int, int, int, int],
]:
    skater_goals: dict[int, int] = defaultdict(int)
    skater_assists: dict[int, int] = defaultdict(int)
    skater_shots: dict[int, int] = defaultdict(int)
    goalie_sa: dict[int, int] = defaultdict(int)
    goalie_saves: dict[int, int] = defaultdict(int)
    goalie_ga: dict[int, int] = defaultdict(int)
    home_shots = away_shots = 0
    home_goals_p = [0, 0, 0, 0]
    away_goals_p = [0, 0, 0, 0]
    home_shots_p = [0, 0, 0, 0]
    away_shots_p = [0, 0, 0, 0]

    for e in events:
        # Period 1..3 regulation, 4 = OT. Clamp for safety.
        pidx = max(1, min(4, e.period)) - 1
        if e.kind in (EventKind.SAVE, EventKind.GOAL):
            if e.primary_skater_id is not None:
                skater_shots[e.primary_skater_id] += 1
            if e.team_is_home:
                home_shots += 1
                home_shots_p[pidx] += 1
            else:
                away_shots += 1
                away_shots_p[pidx] += 1
        if e.kind == EventKind.SAVE and e.goalie_id is not None:
            goalie_sa[e.goalie_id] += 1
            goalie_saves[e.goalie_id] += 1
        if e.kind == EventKind.GOAL:
            if e.team_is_home:
                home_goals_p[pidx] += 1
            else:
                away_goals_p[pidx] += 1
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
    return (
        skater_stats,
        goalie_stats,
        home_shots,
        away_shots,
        tuple(home_goals_p),
        tuple(away_goals_p),
        tuple(home_shots_p),
        tuple(away_shots_p),
    )


def simulate_game(input: SimGameInput) -> SimGameResult:
    rng = random.Random(input.seed)
    events: list[SimEvent] = []
    score = [0, 0]
    home_box = _PenaltyClock(remaining=[], skater_ids=[])
    away_box = _PenaltyClock(remaining=[], skater_ids=[])
    home_st = select_special_teams(input.home.lineup)
    away_st = select_special_teams(input.away.lineup)
    goalie_forms = {
        input.home.lineup.starting_goalie.id: goalie_form_offset(input.home.lineup.starting_goalie, input.seed),
        input.away.lineup.starting_goalie.id: goalie_form_offset(input.away.lineup.starting_goalie, input.seed),
    }

    home_fwd_sched = build_rotation_schedule(
        REGULATION_TICKS, LINE_USAGE_FORWARD_DISTRIBUTION[input.home.gameplan.line_usage]
    )
    home_def_sched = build_rotation_schedule(
        REGULATION_TICKS, LINE_USAGE_DEFENSE_DISTRIBUTION[input.home.gameplan.line_usage]
    )
    away_fwd_sched = build_rotation_schedule(
        REGULATION_TICKS, LINE_USAGE_FORWARD_DISTRIBUTION[input.away.gameplan.line_usage]
    )
    away_def_sched = build_rotation_schedule(
        REGULATION_TICKS, LINE_USAGE_DEFENSE_DISTRIBUTION[input.away.gameplan.line_usage]
    )

    _simulate_phase(
        rng, input.home, input.away, home_st, away_st, home_box, away_box, goalie_forms,
        0, REGULATION_TICKS, events, score, stop_on_goal=False,
        home_fwd_sched=home_fwd_sched, home_def_sched=home_def_sched,
        away_fwd_sched=away_fwd_sched, away_def_sched=away_def_sched,
    )
    result_type = ResultType.REG

    if score[0] == score[1]:
        _simulate_phase(
            rng, input.home, input.away, home_st, away_st, home_box, away_box, goalie_forms,
            REGULATION_TICKS, REGULATION_TICKS + OT_MAX_TICKS, events, score, stop_on_goal=True,
            home_fwd_sched=home_fwd_sched, home_def_sched=home_def_sched,
            away_fwd_sched=away_fwd_sched, away_def_sched=away_def_sched,
        )
        if score[0] != score[1]:
            result_type = ResultType.OT
        else:
            home_strength = sum(line_offense(l) for l in input.home.lineup.forward_lines) - goalie_save_rating(
                input.away.lineup.starting_goalie
            )
            away_strength = sum(line_offense(l) for l in input.away.lineup.forward_lines) - goalie_save_rating(
                input.home.lineup.starting_goalie
            )
            offset = home_strength - away_strength
            home_wins = rng.random() < 0.5 + offset / 1000.0
            if home_wins:
                score[0] += 1
            else:
                score[1] += 1
            result_type = ResultType.SO

    events_t = tuple(events)
    (
        skater_stats,
        goalie_stats,
        home_shots,
        away_shots,
        home_goals_p,
        away_goals_p,
        home_shots_p,
        away_shots_p,
    ) = _aggregate_stats(events_t)

    return SimGameResult(
        home_score=score[0],
        away_score=score[1],
        home_shots=home_shots,
        away_shots=away_shots,
        result_type=result_type,
        events=events_t,
        skater_stats=skater_stats,
        goalie_stats=goalie_stats,
        home_goals_by_period=home_goals_p,
        away_goals_by_period=away_goals_p,
        home_shots_by_period=home_shots_p,
        away_shots_by_period=away_shots_p,
    )
