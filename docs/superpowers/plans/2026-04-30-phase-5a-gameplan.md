# Phase 5A Gameplan / Tactics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-team `gameplan` (style + line usage) that nudges the deterministic simulation in small, statistically visible ways, with the user team's gameplan editable from the Team page.

**Architecture:** Pure sim gains a `SimGameplan` and `SimTeamInput` dataclass (lineup + gameplan). All numeric modifiers live in `backend/sim/constants.py`. `sim/engine.py` reads constants when computing shot probability, shot-quality weights, defensive suppression, and penalty probability. A new `build_rotation_schedule` helper in `sim/rotation.py` keeps line selection schedule-based and deterministic. Service layer adds `team_gameplan` rows at league creation, validates user-team edits, and is loaded by `advance_service` alongside lineups. Frontend adds a Gameplan card to the Team page.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy, Alembic, Pydantic, pytest. Frontend: React + Vite + TypeScript + TanStack Query + Tailwind.

Spec: `docs/superpowers/specs/2026-04-30-phase-5a-gameplan-design.md`.

---

## File Structure

**Backend — create:**
- `backend/sim/constants.py` — `GAMEPLAN_STYLE_MODIFIERS`, `LINE_USAGE_FORWARD_DISTRIBUTION`, `LINE_USAGE_DEFENSE_DISTRIBUTION`.
- `backend/app/models/team_gameplan.py` — `TeamGameplan` SQLAlchemy model.
- `backend/app/services/gameplan_service.py` — read/write/validate.
- `backend/app/api/gameplan.py` — FastAPI router for `/teams/{id}/gameplan`.
- `backend/app/schemas/gameplan.py` — `GameplanOut`, `UpdateGameplanIn`.
- `backend/alembic/versions/d4e5f6a7b8c9_phase5a_team_gameplan.py` — migration.
- `backend/tests/test_gameplan_sim.py` — pure-sim tests.
- `backend/tests/test_gameplan_api.py` — service / API tests.
- `backend/tests/sim/test_rotation_schedule.py` — `build_rotation_schedule` unit tests.
- `frontend/src/queries/gameplan.ts` — TanStack Query hooks.

**Backend — modify:**
- `backend/sim/models.py` — add `SimGameplan`, `SimTeamInput`; change `SimGameInput.home/away` to `SimTeamInput`.
- `backend/sim/rotation.py` — add `build_rotation_schedule`; keep `period_at_tick`. Existing `forward_line_at_tick` / `defense_pair_at_tick` retained for any non-engine callers but no longer used by engine.
- `backend/sim/engine.py` — accept `SimTeamInput`; thread gameplan through shot-probability, shot-quality, suppression, penalty, and rotation logic.
- `backend/app/models/__init__.py` — export `TeamGameplan`.
- `backend/app/errors.py` — add `GameplanInvalid`, `NotUserTeam`.
- `backend/app/services/league_service.py` — call `generate_gameplans_for_league` after teams generated.
- `backend/app/services/advance_service.py` — load gameplans, build `SimTeamInput`.
- `backend/app/main.py` (or wherever routers are mounted) — include the new router.
- `backend/tests/sim/test_engine_determinism.py` — update `_team` helper to return `SimTeamInput`.

**Frontend — modify:**
- `frontend/src/api/types.ts` — add `Gameplan` types.
- `frontend/src/routes/team.$teamId.tsx` — add Gameplan card.

---

## Pre-flight

- [ ] **Step 1: Run baseline tests**

```bash
cd backend && uv run pytest -q
```

Expected: all currently-passing. (Should be 94 pass at the time this plan runs; if not, stop.)

- [ ] **Step 2: Confirm clean tree**

```bash
git status
```

Expected: clean (or only the spec/plan).

---

## Task 1: Sim constants module

**Files:** Create `backend/sim/constants.py`.

- [ ] **Step 1: Write the constants module**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/sim/constants.py
git commit -m "feat(sim): add gameplan style and line-usage constants"
```

---

## Task 2: Pure rotation schedule helper + tests

**Files:** Modify `backend/sim/rotation.py`. Create `backend/tests/sim/test_rotation_schedule.py`.

- [ ] **Step 1: Write failing tests**

Create `backend/tests/sim/test_rotation_schedule.py`:

```python
from sim.rotation import build_rotation_schedule


def test_counts_match_distribution_for_clean_split():
    sched = build_rotation_schedule(180, (0.40, 0.30, 0.20, 0.10))
    counts = [sched.count(i) for i in range(4)]
    assert counts == [72, 54, 36, 18]
    assert len(sched) == 180


def test_counts_sum_when_distribution_doesnt_round_clean():
    sched = build_rotation_schedule(15, (0.30, 0.27, 0.23, 0.20))
    assert len(sched) == 15
    counts = [sched.count(i) for i in range(4)]
    assert sum(counts) == 15
    # No bucket should be empty for non-zero weight on a 15-tick schedule.
    assert all(c >= 1 for c in counts)


def test_no_long_clustering():
    sched = build_rotation_schedule(180, (0.40, 0.30, 0.20, 0.10))
    # No more than 4 consecutive identical indices.
    run = 1
    max_run = 1
    for a, b in zip(sched, sched[1:]):
        if a == b:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 1
    assert max_run <= 4


def test_deterministic_across_calls():
    a = build_rotation_schedule(180, (0.40, 0.30, 0.20, 0.10))
    b = build_rotation_schedule(180, (0.40, 0.30, 0.20, 0.10))
    assert a == b


def test_returns_tuple():
    sched = build_rotation_schedule(60, (0.45, 0.35, 0.20))
    assert isinstance(sched, tuple)
    assert all(isinstance(i, int) for i in sched)
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend && uv run pytest tests/sim/test_rotation_schedule.py -q
```

Expected: ImportError (function not yet defined).

- [ ] **Step 3: Implement `build_rotation_schedule`**

Append to `backend/sim/rotation.py`:

```python
def build_rotation_schedule(
    total_ticks: int, distribution: tuple[float, ...]
) -> tuple[int, ...]:
    """Return a deterministic per-tick schedule of line indices.

    Each line index appears `round(total_ticks * distribution[i])` times,
    with the largest bucket adjusted so the counts sum to total_ticks.
    Indices are interleaved (Bresenham-style) so any short window
    approximates the configured distribution.
    """
    if total_ticks <= 0:
        return ()
    n = len(distribution)
    if n == 0:
        return tuple([0] * total_ticks)

    # Exact target counts.
    counts = [round(total_ticks * w) for w in distribution]
    diff = total_ticks - sum(counts)
    if diff != 0:
        # Adjust the largest bucket so totals match exactly.
        idx = max(range(n), key=lambda i: counts[i])
        counts[idx] += diff
    # Guarantee non-negative counts after adjustment.
    counts = [max(0, c) for c in counts]
    # If rounding zeroed all buckets (degenerate), fall back to all-zero.
    if sum(counts) == 0:
        return tuple([0] * total_ticks)
    # Re-fix sum if clamping changed it.
    while sum(counts) < total_ticks:
        idx = max(range(n), key=lambda i: counts[i])
        counts[idx] += 1
    while sum(counts) > total_ticks:
        idx = max(range(n), key=lambda i: counts[i])
        counts[idx] -= 1

    # Bresenham-style interleave: track an "error" per bucket; at each tick
    # pick the bucket with the largest remaining_count / total_remaining.
    remaining = list(counts)
    out: list[int] = []
    for _ in range(total_ticks):
        # Pick bucket with highest fractional share remaining; tiebreak by
        # lower index to stay deterministic.
        total_remaining = sum(remaining)
        best_i = 0
        best_share = -1.0
        for i, r in enumerate(remaining):
            if r <= 0:
                continue
            share = r / total_remaining
            if share > best_share + 1e-12:
                best_share = share
                best_i = i
        out.append(best_i)
        remaining[best_i] -= 1
    return tuple(out)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/sim/test_rotation_schedule.py -q
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/sim/rotation.py backend/tests/sim/test_rotation_schedule.py
git commit -m "feat(sim): add deterministic build_rotation_schedule helper"
```

---

## Task 3: SimGameplan + SimTeamInput dataclasses

**Files:** Modify `backend/sim/models.py`.

- [ ] **Step 1: Add types and replace `SimGameInput`**

Edit `backend/sim/models.py`. Add `from typing import Literal` near the top imports if missing. Then add these two dataclasses **above** `SimGameInput`:

```python
@dataclass(frozen=True)
class SimGameplan:
    style: str  # "balanced" | "offensive" | "defensive" | "physical"
    line_usage: str  # "balanced" | "ride_top_lines" | "roll_all_lines"


@dataclass(frozen=True)
class SimTeamInput:
    lineup: SimTeamLineup
    gameplan: SimGameplan
```

Replace `SimGameInput`:

```python
@dataclass(frozen=True)
class SimGameInput:
    home: SimTeamInput
    away: SimTeamInput
    seed: int
```

(Note: `Literal` types in dataclasses are runtime-noop in Python; using plain `str` plus validation in the service layer keeps the sim independent of typing extras.)

- [ ] **Step 2: Update `_team` helper in tests to return `SimTeamInput`**

Edit `backend/tests/sim/test_engine_determinism.py`:

```python
from sim.engine import simulate_game
from sim.models import (
    Position,
    SimGameInput,
    SimGameplan,
    SimGoalie,
    SimLine,
    SimSkater,
    SimTeamInput,
    SimTeamLineup,
)


def _team(off_id_base: int, gameplan: SimGameplan | None = None) -> SimTeamInput:
    fwd = lambda i, p: SimSkater(id=i, position=p, skating=75, shooting=75, passing=75, defense=60, physical=65)
    dfn = lambda i: SimSkater(id=i, position=Position.LD, skating=70, shooting=60, passing=65, defense=80, physical=75)
    forward_lines = tuple(
        SimLine(
            skaters=(
                fwd(off_id_base + i * 3 + 0, Position.LW),
                fwd(off_id_base + i * 3 + 1, Position.C),
                fwd(off_id_base + i * 3 + 2, Position.RW),
            )
        )
        for i in range(4)
    )
    pairs = tuple(SimLine(skaters=(dfn(off_id_base + 100 + i * 2), dfn(off_id_base + 101 + i * 2))) for i in range(3))
    g = SimGoalie(id=off_id_base + 200, reflexes=80, positioning=80, rebound_control=70, puck_handling=60, mental=75)
    lineup = SimTeamLineup(forward_lines=forward_lines, defense_pairs=pairs, starting_goalie=g)
    return SimTeamInput(lineup=lineup, gameplan=gameplan or SimGameplan("balanced", "balanced"))
```

The two existing tests in that file (`test_same_seed_same_result`, `test_different_seed_different_result`) use `_team(...)` and continue to work because the call sites already match the new shape. No code change needed in those test bodies, since `SimGameInput(home=_team(...))` now receives a `SimTeamInput`.

- [ ] **Step 3: Run dataclass-only smoke**

```bash
uv run python -c "from sim.models import SimGameplan, SimTeamInput; print(SimGameplan('balanced','balanced'))"
```

Expected: prints `SimGameplan(style='balanced', line_usage='balanced')`.

- [ ] **Step 4: Commit (engine still broken at this point — fixed in Task 4)**

```bash
git add backend/sim/models.py backend/tests/sim/test_engine_determinism.py
git commit -m "feat(sim): add SimGameplan and SimTeamInput dataclasses"
```

---

## Task 4: Engine integration — accept SimTeamInput, apply gameplan modifiers

**Files:** Modify `backend/sim/engine.py`.

- [ ] **Step 1: Update imports and helper functions to use gameplan**

Edit `backend/sim/engine.py`:

Add to imports:

```python
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
from sim.rotation import (
    REGULATION_TICKS,
    build_rotation_schedule,
    period_at_tick,
)
```

Remove the `from sim.rotation import ... defense_pair_at_tick, forward_line_at_tick, ...` line (replaced above).

- [ ] **Step 2: Replace `_on_ice` and add per-team rotation schedule plumbing**

Replace the `_on_ice` helper and threading. New helpers near the top of the file:

```python
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
```

Delete the existing `_on_ice` function.

- [ ] **Step 3: Apply defensive suppression once, in `_on_ice_attackers_and_def`**

Replace the body of `_on_ice_attackers_and_def` so it accepts the schedules and applies the defender's `def_suppression` exactly once on the returned `deff` value:

```python
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
    """Returns (attacking forwards, defending skaters used for penalty draws,
    defender's defensive rating used for shot-prob)."""
    if strength == Strength.PP:
        attackers = list(attacker_st.pp_forwards)
        defenders = list(defender_st.pk_defense)
        deff = pk_unit_defense(defender_st)
    elif strength == Strength.SH:
        attackers = list(attacker_st.pk_forwards)
        defenders = list(defender_st.pp_defense)
        deff = pair_defense(SimLine(skaters=defender_st.pp_defense))
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
```

- [ ] **Step 4: Update `_attempt_shot` to apply style shot_prob modifiers and shot-quality tilt**

Replace `_attempt_shot` and `_classify_shot_quality`:

```python
def _classify_shot_quality(
    rng: random.Random,
    off: float,
    deff: float,
    strength: Strength,
    attacker_gp: SimGameplan,
    defender_gp: SimGameplan,
) -> ShotQuality:
    margin = (off - deff) / 30.0
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
    off = sum(0.5 * s.shooting + 0.3 * s.passing + 0.2 * s.skating for s in attackers) / len(attackers)
    shot_prob = _shot_probability(off, defender_def)
    if strength == Strength.PP:
        shot_prob *= SHOT_PROB_PP
    elif strength == Strength.SH:
        shot_prob *= SHOT_PROB_SH
    # Style modifiers on shot probability (multiplicative, applied once each).
    shot_prob *= _style_mod(attacker_gp, "shot_prob") * _style_mod(defender_gp, "opp_shot_prob")
    if rng.random() > shot_prob:
        return (None, None, [], 0, None)

    shooter = _pick_weighted(rng, attackers, [s.shooting for s in attackers])
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
```

- [ ] **Step 5: Update `_maybe_penalty` to apply gameplan-averaged penalty probability**

Replace the body of `_maybe_penalty`:

```python
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
    pool = attackers + defenders
    weights = [s.physical for s in pool]
    offender = _pick_weighted(rng, pool, weights)
    is_attacker = offender in attackers
    box = attacker_box if is_attacker else defender_box
    box.add(offender.id)
    return (is_attacker, offender.id)
```

- [ ] **Step 6: Thread gameplan through `_run_tick` and `_simulate_phase`**

Replace `_run_tick` signature and body:

```python
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
```

Replace `_simulate_phase` signature/body:

```python
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
        h_fwd_idx = home_fwd_sched[t % len(home_fwd_sched)]
        a_fwd_idx = away_fwd_sched[t % len(away_fwd_sched)]
        h_fwd = home.lineup.forward_lines[h_fwd_idx]
        a_fwd = away.lineup.forward_lines[a_fwd_idx]
        h_weight = sum(s.skating for s in h_fwd.skaters)
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
```

- [ ] **Step 7: Update `simulate_game` to build schedules and pass `SimTeamInput`**

Replace `simulate_game`:

```python
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
```

- [ ] **Step 8: Update advance_service to wrap lineups in SimTeamInput**

Edit `backend/app/services/advance_service.py`. Add to imports:

```python
from sim.models import (
    Position,
    ResultType,
    SimGameInput,
    SimGameplan,
    SimGoalie,
    SimLine,
    SimSkater,
    SimTeamInput,
    SimTeamLineup,
)
```

(Replace the existing imports of those names — just add `SimGameplan, SimTeamInput`.)

Inside `advance_matchday`, replace the line that builds the `SimGameInput`:

```python
home_lu = _build_lineup(db, g.home_team_id)
away_lu = _build_lineup(db, g.away_team_id)
seed = derive_game_seed(season.seed, g.id)
result = simulate_game(SimGameInput(home=home_lu, away=away_lu, seed=seed))
```

becomes (temporary — Task 9 will swap defaults for real DB-backed gameplans):

```python
home_lu = _build_lineup(db, g.home_team_id)
away_lu = _build_lineup(db, g.away_team_id)
seed = derive_game_seed(season.seed, g.id)
default_gp = SimGameplan(style="balanced", line_usage="balanced")
result = simulate_game(
    SimGameInput(
        home=SimTeamInput(lineup=home_lu, gameplan=default_gp),
        away=SimTeamInput(lineup=away_lu, gameplan=default_gp),
        seed=seed,
    )
)
```

- [ ] **Step 9: Run all sim and service tests**

```bash
uv run pytest tests/sim tests/services -q
```

Expected: existing sim tests still pass (gameplan defaults to balanced/balanced via the `_team` helper); existing service tests still pass.

- [ ] **Step 10: Commit**

```bash
git add backend/sim/engine.py backend/app/services/advance_service.py
git commit -m "feat(sim): thread gameplan through engine; defaults preserve old behavior"
```

---

## Task 5: Pure-sim gameplan tests

**Files:** Create `backend/tests/test_gameplan_sim.py`.

- [ ] **Step 1: Write the tests**

```python
"""Broad statistical tests of gameplan effects on the pure simulation."""
from sim.engine import simulate_game
from sim.models import EventKind, SimGameInput, SimGameplan, SimTeamInput
from tests.sim.test_engine_determinism import _team


def _input(seed: int, home_gp: SimGameplan, away_gp: SimGameplan) -> SimGameInput:
    h = _team(1000, gameplan=home_gp)
    a = _team(2000, gameplan=away_gp)
    return SimGameInput(home=h, away=a, seed=seed)


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def test_determinism_with_gameplan():
    gp = SimGameplan("offensive", "ride_top_lines")
    inp = _input(99, gp, SimGameplan("balanced", "balanced"))
    a = simulate_game(inp)
    b = simulate_game(inp)
    assert a == b


def test_offensive_increases_shots_for():
    n = 100
    off_shots: list[int] = []
    bal_shots: list[int] = []
    for s in range(n):
        off_shots.append(simulate_game(_input(s, SimGameplan("offensive", "balanced"), SimGameplan("balanced", "balanced"))).home_shots)
        bal_shots.append(simulate_game(_input(s, SimGameplan("balanced", "balanced"), SimGameplan("balanced", "balanced"))).home_shots)
    assert _mean(off_shots) > _mean(bal_shots)


def test_defensive_decreases_shots_against():
    n = 100
    def_against: list[int] = []
    bal_against: list[int] = []
    for s in range(n):
        def_against.append(simulate_game(_input(s, SimGameplan("defensive", "balanced"), SimGameplan("balanced", "balanced"))).away_shots)
        bal_against.append(simulate_game(_input(s, SimGameplan("balanced", "balanced"), SimGameplan("balanced", "balanced"))).away_shots)
    assert _mean(def_against) < _mean(bal_against)


def test_physical_increases_total_penalties():
    n = 100
    phys: list[int] = []
    bal: list[int] = []
    for s in range(n):
        phys_res = simulate_game(_input(s, SimGameplan("physical", "balanced"), SimGameplan("physical", "balanced")))
        bal_res = simulate_game(_input(s, SimGameplan("balanced", "balanced"), SimGameplan("balanced", "balanced")))
        phys.append(sum(1 for e in phys_res.events if e.kind == EventKind.PENALTY))
        bal.append(sum(1 for e in bal_res.events if e.kind == EventKind.PENALTY))
    assert _mean(phys) > _mean(bal)


def _line1_skater_ids(team_input: SimTeamInput) -> set[int]:
    return {s.id for s in team_input.lineup.forward_lines[0].skaters}


def _line4_skater_ids(team_input: SimTeamInput) -> set[int]:
    return {s.id for s in team_input.lineup.forward_lines[3].skaters}


def test_ride_top_lines_increases_top_line_involvement():
    n = 60
    ride = []
    bal = []
    for s in range(n):
        h_ride = _team(1000, gameplan=SimGameplan("balanced", "ride_top_lines"))
        a_def = _team(2000, gameplan=SimGameplan("balanced", "balanced"))
        h_bal = _team(1000, gameplan=SimGameplan("balanced", "balanced"))
        ride_res = simulate_game(SimGameInput(home=h_ride, away=a_def, seed=s))
        bal_res = simulate_game(SimGameInput(home=h_bal, away=a_def, seed=s))
        line1_ids = _line1_skater_ids(h_ride)
        ride.append(sum(st.shots for st in ride_res.skater_stats if st.skater_id in line1_ids))
        bal.append(sum(st.shots for st in bal_res.skater_stats if st.skater_id in line1_ids))
    assert _mean(ride) > _mean(bal)


def test_roll_all_lines_increases_line4_involvement():
    n = 60
    roll = []
    bal = []
    for s in range(n):
        h_roll = _team(1000, gameplan=SimGameplan("balanced", "roll_all_lines"))
        a = _team(2000, gameplan=SimGameplan("balanced", "balanced"))
        h_bal = _team(1000, gameplan=SimGameplan("balanced", "balanced"))
        roll_res = simulate_game(SimGameInput(home=h_roll, away=a, seed=s))
        bal_res = simulate_game(SimGameInput(home=h_bal, away=a, seed=s))
        line4_ids = _line4_skater_ids(h_roll)
        roll.append(sum(st.shots for st in roll_res.skater_stats if st.skater_id in line4_ids))
        bal.append(sum(st.shots for st in bal_res.skater_stats if st.skater_id in line4_ids))
    assert _mean(roll) > _mean(bal)


def test_player_quality_dominates_gameplan():
    """A strong defensive team should still beat a weak offensive team."""
    from sim.models import Position, SimGoalie, SimLine, SimSkater, SimTeamLineup

    def strong_team() -> SimTeamInput:
        fwd = lambda i, p: SimSkater(id=i, position=p, skating=85, shooting=85, passing=85, defense=70, physical=75)
        dfn = lambda i: SimSkater(id=i, position=Position.LD, skating=80, shooting=70, passing=75, defense=90, physical=85)
        forward_lines = tuple(
            SimLine(skaters=(fwd(3000 + i*3 + 0, Position.LW), fwd(3000 + i*3 + 1, Position.C), fwd(3000 + i*3 + 2, Position.RW)))
            for i in range(4)
        )
        pairs = tuple(SimLine(skaters=(dfn(3100 + i*2), dfn(3101 + i*2))) for i in range(3))
        g = SimGoalie(id=3200, reflexes=88, positioning=88, rebound_control=80, puck_handling=70, mental=85)
        return SimTeamInput(
            lineup=SimTeamLineup(forward_lines=forward_lines, defense_pairs=pairs, starting_goalie=g),
            gameplan=SimGameplan("defensive", "balanced"),
        )

    def weak_team() -> SimTeamInput:
        fwd = lambda i, p: SimSkater(id=i, position=p, skating=65, shooting=65, passing=65, defense=55, physical=55)
        dfn = lambda i: SimSkater(id=i, position=Position.LD, skating=60, shooting=55, passing=60, defense=70, physical=65)
        forward_lines = tuple(
            SimLine(skaters=(fwd(4000 + i*3 + 0, Position.LW), fwd(4000 + i*3 + 1, Position.C), fwd(4000 + i*3 + 2, Position.RW)))
            for i in range(4)
        )
        pairs = tuple(SimLine(skaters=(dfn(4100 + i*2), dfn(4101 + i*2))) for i in range(3))
        g = SimGoalie(id=4200, reflexes=70, positioning=70, rebound_control=65, puck_handling=60, mental=65)
        return SimTeamInput(
            lineup=SimTeamLineup(forward_lines=forward_lines, defense_pairs=pairs, starting_goalie=g),
            gameplan=SimGameplan("offensive", "balanced"),
        )

    n = 60
    diffs = []
    for s in range(n):
        r = simulate_game(SimGameInput(home=strong_team(), away=weak_team(), seed=s))
        diffs.append(r.home_score - r.away_score)
    assert _mean(diffs) > 0


def test_shot_quality_weights_stay_positive_with_offensive_and_defensive():
    """Smoke: offensive vs defensive run for many seeds without crashing
    (would crash on a zero-sum weight inside random.choices)."""
    for s in range(30):
        simulate_game(_input(s, SimGameplan("offensive", "balanced"), SimGameplan("defensive", "balanced")))
```

- [ ] **Step 2: Run the new tests**

```bash
cd backend && uv run pytest tests/test_gameplan_sim.py -q
```

Expected: 8 passed. (If a statistical comparison flakes, the deltas in `sim/constants.py` are intentionally small but the sample sizes here are sized to make these comparisons stable. If a flake occurs, increase n by 50%.)

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_gameplan_sim.py
git commit -m "feat(sim): add broad gameplan effect tests"
```

---

## Task 6: TeamGameplan model

**Files:** Create `backend/app/models/team_gameplan.py`. Modify `backend/app/models/__init__.py`.

- [ ] **Step 1: Write the model**

`backend/app/models/team_gameplan.py`:

```python
from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TeamGameplan(Base):
    __tablename__ = "team_gameplan"
    __table_args__ = (
        UniqueConstraint("team_id", name="uq_team_gameplan_team_id"),
        CheckConstraint(
            "style IN ('balanced', 'offensive', 'defensive', 'physical')",
            name="ck_team_gameplan_style",
        ),
        CheckConstraint(
            "line_usage IN ('balanced', 'ride_top_lines', 'roll_all_lines')",
            name="ck_team_gameplan_line_usage",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("team.id", ondelete="CASCADE"), index=True, nullable=False
    )
    style: Mapped[str] = mapped_column(String(16), nullable=False)
    line_usage: Mapped[str] = mapped_column(String(16), nullable=False)
```

- [ ] **Step 2: Export from `models/__init__.py`**

Edit `backend/app/models/__init__.py`. Add the import in alphabetical order and the name to `__all__`:

```python
from app.models.team_gameplan import TeamGameplan
```

and add `"TeamGameplan",` to `__all__`.

- [ ] **Step 3: Smoke import**

```bash
uv run python -c "from app.models import TeamGameplan; print(TeamGameplan.__tablename__)"
```

Expected: prints `team_gameplan`.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/team_gameplan.py backend/app/models/__init__.py
git commit -m "feat(models): add team_gameplan with CHECK constraints"
```

---

## Task 7: Alembic migration

**Files:** Create `backend/alembic/versions/d4e5f6a7b8c9_phase5a_team_gameplan.py`.

- [ ] **Step 1: Find the latest revision id**

```bash
ls backend/alembic/versions
```

Expected to include `c3d4e5f6a7b8_phase4_player_development.py` (Phase 4). Use that revision id as `down_revision`.

- [ ] **Step 2: Write the migration**

```python
"""phase 5A: team_gameplan

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-30 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "team_gameplan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "team_id",
            sa.Integer(),
            sa.ForeignKey("team.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("style", sa.String(length=16), nullable=False),
        sa.Column("line_usage", sa.String(length=16), nullable=False),
        sa.UniqueConstraint("team_id", name="uq_team_gameplan_team_id"),
        sa.CheckConstraint(
            "style IN ('balanced', 'offensive', 'defensive', 'physical')",
            name="ck_team_gameplan_style",
        ),
        sa.CheckConstraint(
            "line_usage IN ('balanced', 'ride_top_lines', 'roll_all_lines')",
            name="ck_team_gameplan_line_usage",
        ),
    )
    op.create_index("ix_team_gameplan_team_id", "team_gameplan", ["team_id"])
    op.execute(
        """
        INSERT INTO team_gameplan (team_id, style, line_usage)
        SELECT t.id, 'balanced', 'balanced'
        FROM team t
        WHERE NOT EXISTS (
            SELECT 1 FROM team_gameplan tg WHERE tg.team_id = t.id
        )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_team_gameplan_team_id", table_name="team_gameplan")
    op.drop_table("team_gameplan")
```

- [ ] **Step 3: Apply locally**

```bash
cd backend && uv run alembic upgrade head
```

Expected: applies cleanly. Verify in a Python shell:

```bash
uv run python -c "
from app.db import engine
from sqlalchemy import inspect
print(sorted(inspect(engine).get_columns('team_gameplan'), key=lambda c: c['name']))
"
```

Expected: 4 columns including `style` and `line_usage`.

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/d4e5f6a7b8c9_phase5a_team_gameplan.py
git commit -m "feat(migration): add team_gameplan table with CHECK constraints"
```

---

## Task 8: Errors and Pydantic schemas

**Files:** Modify `backend/app/errors.py`. Create `backend/app/schemas/gameplan.py`.

- [ ] **Step 1: Add error classes**

Append to `backend/app/errors.py`:

```python
class GameplanInvalid(DomainError):
    code = "GameplanInvalid"
    status = 422


class NotUserTeam(DomainError):
    code = "NotUserTeam"
    status = 403
```

- [ ] **Step 2: Add schemas**

Create `backend/app/schemas/gameplan.py`:

```python
from typing import Literal

from pydantic import BaseModel

GameplanStyle = Literal["balanced", "offensive", "defensive", "physical"]
GameplanLineUsage = Literal["balanced", "ride_top_lines", "roll_all_lines"]


class GameplanOut(BaseModel):
    team_id: int
    style: GameplanStyle
    line_usage: GameplanLineUsage
    editable: bool


class UpdateGameplanIn(BaseModel):
    style: GameplanStyle
    line_usage: GameplanLineUsage
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/errors.py backend/app/schemas/gameplan.py
git commit -m "feat(api): add gameplan errors and pydantic schemas"
```

---

## Task 9: Gameplan service

**Files:** Create `backend/app/services/gameplan_service.py`. Modify `backend/app/services/league_service.py`. Modify `backend/app/services/advance_service.py`.

- [ ] **Step 1: Write service**

```python
import random

from sqlalchemy.orm import Session

from app.errors import GameplanInvalid, NotUserTeam, TeamNotFound
from app.models import Season, Team, TeamGameplan

ALLOWED_STYLES = ("balanced", "offensive", "defensive", "physical")
ALLOWED_LINE_USAGES = ("balanced", "ride_top_lines", "roll_all_lines")

_STYLE_WEIGHTS = [
    ("balanced", 0.50),
    ("offensive", 0.20),
    ("defensive", 0.20),
    ("physical", 0.10),
]
_LINE_USAGE_WEIGHTS = [
    ("balanced", 0.60),
    ("ride_top_lines", 0.25),
    ("roll_all_lines", 0.15),
]


def _sample(rng: random.Random, weighted: list[tuple[str, float]]) -> str:
    r = rng.random()
    acc = 0.0
    for name, w in weighted:
        acc += w
        if r < acc:
            return name
    return weighted[-1][0]


def _validate(style: str, line_usage: str) -> None:
    if style not in ALLOWED_STYLES:
        raise GameplanInvalid(f"unknown style {style!r}")
    if line_usage not in ALLOWED_LINE_USAGES:
        raise GameplanInvalid(f"unknown line_usage {line_usage!r}")


def _current_user_team_id(db: Session) -> int | None:
    season = db.query(Season).order_by(Season.id.desc()).first()
    return season.user_team_id if season else None


def get_team_gameplan(db: Session, team_id: int) -> TeamGameplan:
    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        raise TeamNotFound(f"team {team_id} not found")
    gp = db.query(TeamGameplan).filter_by(team_id=team_id).first()
    if not gp:
        # Self-heal: insert a balanced/balanced row (covers any team that
        # somehow predates the migration backfill).
        gp = TeamGameplan(team_id=team_id, style="balanced", line_usage="balanced")
        db.add(gp)
        db.flush()
    return gp


def update_user_team_gameplan(
    db: Session, team_id: int, style: str, line_usage: str
) -> TeamGameplan:
    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        raise TeamNotFound(f"team {team_id} not found")
    if _current_user_team_id(db) != team_id:
        raise NotUserTeam(f"team {team_id} is not the user team")
    _validate(style, line_usage)
    gp = get_team_gameplan(db, team_id)
    gp.style = style
    gp.line_usage = line_usage
    db.flush()
    return gp


def is_editable(db: Session, team_id: int) -> bool:
    return _current_user_team_id(db) == team_id


def generate_gameplans_for_league(
    rng: random.Random, db: Session, team_ids: list[int], user_team_id: int | None
) -> None:
    """Idempotent. Wipes existing rows for the supplied team_ids and inserts
    fresh gameplans. The user team always gets (balanced, balanced)."""
    if team_ids:
        db.query(TeamGameplan).filter(TeamGameplan.team_id.in_(team_ids)).delete(
            synchronize_session=False
        )
    for tid in team_ids:
        if tid == user_team_id:
            db.add(TeamGameplan(team_id=tid, style="balanced", line_usage="balanced"))
        else:
            db.add(
                TeamGameplan(
                    team_id=tid,
                    style=_sample(rng, _STYLE_WEIGHTS),
                    line_usage=_sample(rng, _LINE_USAGE_WEIGHTS),
                )
            )
    db.flush()
```

- [ ] **Step 2: Wire into `create_or_reset_league`**

Edit `backend/app/services/league_service.py`. Add to imports:

```python
from app.services.gameplan_service import generate_gameplans_for_league
```

In `_wipe`, ensure `TeamGameplan` is wiped before `Team` (cascade on FK does this, but be explicit so order is obvious). Add to the model list at the top of `_wipe`:

```python
def _wipe(db: Session) -> None:
    from app.models import TeamGameplan  # local import keeps top-of-module clean

    for model in [
        GameEvent,
        SkaterGameStat,
        GoalieGameStat,
        Game,
        Standing,
        Lineup,
        Skater,
        Goalie,
        TeamGameplan,
        Team,
        Season,
    ]:
        db.execute(delete(model))
```

In `create_or_reset_league`, after `for t in teams: db.add(Standing(...))` and after `season.user_team_id = teams[0].id`, add:

```python
generate_gameplans_for_league(
    rng, db, [t.id for t in teams], user_team_id=season.user_team_id
)
```

- [ ] **Step 3: Wire DB-backed gameplans into advance_service**

Edit `backend/app/services/advance_service.py`. Add to imports:

```python
from app.models import TeamGameplan
```

Replace the temporary `default_gp` block from Task 4 with a real loader:

```python
def _gameplan_for(db: Session, team_id: int) -> SimGameplan:
    gp = db.query(TeamGameplan).filter_by(team_id=team_id).first()
    if gp is None:
        return SimGameplan(style="balanced", line_usage="balanced")
    return SimGameplan(style=gp.style, line_usage=gp.line_usage)
```

Place that helper near `_to_sim_skater`. Then in `advance_matchday`, replace the simulate_game call:

```python
home_lu = _build_lineup(db, g.home_team_id)
away_lu = _build_lineup(db, g.away_team_id)
seed = derive_game_seed(season.seed, g.id)
home_gp = _gameplan_for(db, g.home_team_id)
away_gp = _gameplan_for(db, g.away_team_id)
result = simulate_game(
    SimGameInput(
        home=SimTeamInput(lineup=home_lu, gameplan=home_gp),
        away=SimTeamInput(lineup=away_lu, gameplan=away_gp),
        seed=seed,
    )
)
```

- [ ] **Step 4: Run tests**

```bash
cd backend && uv run pytest -q
```

Expected: all pass. (`create_or_reset_league` now seeds gameplans; `advance_service` loads them; existing test fixtures that go through `create_or_reset_league` get balanced/balanced for the user team and randomized values for the rest.)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/gameplan_service.py backend/app/services/league_service.py backend/app/services/advance_service.py
git commit -m "feat(services): add gameplan service; seed at league creation; load in advance"
```

---

## Task 10: Gameplan API router

**Files:** Create `backend/app/api/gameplan.py`. Modify `backend/app/main.py` (or wherever routers are mounted).

- [ ] **Step 1: Inspect router mounting**

```bash
grep -rn "include_router" backend/app/main.py 2>/dev/null || grep -rn "include_router" backend/app/
```

Note where existing routers (league, season, players) are wired so the new one matches.

- [ ] **Step 2: Write the router**

`backend/app/api/gameplan.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.gameplan import GameplanOut, UpdateGameplanIn
from app.services import gameplan_service

router = APIRouter(prefix="/teams", tags=["gameplan"])


def _to_out(gp, editable: bool) -> GameplanOut:
    return GameplanOut(
        team_id=gp.team_id,
        style=gp.style,
        line_usage=gp.line_usage,
        editable=editable,
    )


@router.get("/{team_id}/gameplan", response_model=GameplanOut)
def get_gameplan(team_id: int, db: Session = Depends(get_db)):
    gp = gameplan_service.get_team_gameplan(db, team_id)
    return _to_out(gp, gameplan_service.is_editable(db, team_id))


@router.put("/{team_id}/gameplan", response_model=GameplanOut)
def put_gameplan(team_id: int, payload: UpdateGameplanIn, db: Session = Depends(get_db)):
    gp = gameplan_service.update_user_team_gameplan(
        db, team_id, payload.style, payload.line_usage
    )
    db.commit()
    return _to_out(gp, editable=True)
```

- [ ] **Step 3: Mount the router**

In the file from Step 1, add:

```python
from app.api.gameplan import router as gameplan_router
# ...
app.include_router(gameplan_router, prefix="/api")
```

(Use the same prefix convention as the existing routers — likely `/api`.)

- [ ] **Step 4: Smoke import**

```bash
uv run python -c "from app.main import app; print([r.path for r in app.routes if 'gameplan' in r.path])"
```

Expected: includes `/api/teams/{team_id}/gameplan` for both GET and PUT.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/gameplan.py backend/app/main.py
git commit -m "feat(api): add /api/teams/{id}/gameplan GET and PUT"
```

---

## Task 11: API and service tests

**Files:** Create `backend/tests/test_gameplan_api.py`.

- [ ] **Step 1: Write the tests**

```python
import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.errors import GameplanInvalid, NotUserTeam, TeamNotFound
from app.main import app
from app.models import Team, TeamGameplan
from app.services import gameplan_service, season_rollover_service
from app.services.advance_service import advance_matchday
from app.services.league_service import create_or_reset_league


def test_league_creation_seeds_gameplans(db):
    season = create_or_reset_league(db, seed=314)
    db.flush()
    team_count = db.query(Team).count()
    gp_count = db.query(TeamGameplan).count()
    assert gp_count == team_count
    user_gp = (
        db.query(TeamGameplan).filter_by(team_id=season.user_team_id).one()
    )
    assert user_gp.style == "balanced"
    assert user_gp.line_usage == "balanced"


def test_get_gameplan_marks_editable_correctly(db):
    season = create_or_reset_league(db, seed=315)
    db.flush()

    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)
        # User team
        r = client.get(f"/api/teams/{season.user_team_id}/gameplan")
        assert r.status_code == 200
        assert r.json()["editable"] is True
        # Non-user team
        other = (
            db.query(Team).filter(Team.id != season.user_team_id).order_by(Team.id).first()
        )
        r = client.get(f"/api/teams/{other.id}/gameplan")
        assert r.status_code == 200
        assert r.json()["editable"] is False
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_put_gameplan_user_team_persists(db):
    season = create_or_reset_league(db, seed=316)
    db.flush()

    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)
        r = client.put(
            f"/api/teams/{season.user_team_id}/gameplan",
            json={"style": "offensive", "line_usage": "ride_top_lines"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["style"] == "offensive"
        assert body["line_usage"] == "ride_top_lines"
        gp = (
            db.query(TeamGameplan).filter_by(team_id=season.user_team_id).one()
        )
        assert gp.style == "offensive"
        assert gp.line_usage == "ride_top_lines"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_put_gameplan_on_non_user_team_returns_403(db):
    season = create_or_reset_league(db, seed=317)
    db.flush()
    other = (
        db.query(Team).filter(Team.id != season.user_team_id).order_by(Team.id).first()
    )

    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)
        r = client.put(
            f"/api/teams/{other.id}/gameplan",
            json={"style": "offensive", "line_usage": "balanced"},
        )
        assert r.status_code == 403
        assert r.json()["error_code"] == "NotUserTeam"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_put_gameplan_invalid_style_returns_422(db):
    season = create_or_reset_league(db, seed=318)
    db.flush()

    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)
        r = client.put(
            f"/api/teams/{season.user_team_id}/gameplan",
            json={"style": "kamikaze", "line_usage": "balanced"},
        )
        assert r.status_code == 422
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_get_gameplan_unknown_team_returns_404(db):
    create_or_reset_league(db, seed=319)
    db.flush()

    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)
        r = client.get("/api/teams/9999999/gameplan")
        assert r.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_rollover_preserves_gameplans(db):
    season = create_or_reset_league(db, seed=2026)
    db.flush()
    before = {
        gp.team_id: (gp.style, gp.line_usage)
        for gp in db.query(TeamGameplan).all()
    }
    while advance_matchday(db)["season_status"] != "complete":
        pass
    db.commit()
    season_rollover_service.start_next_season(db)
    db.commit()
    after = {
        gp.team_id: (gp.style, gp.line_usage)
        for gp in db.query(TeamGameplan).all()
    }
    assert before == after


def test_set_user_team_does_not_change_gameplans(db):
    season = create_or_reset_league(db, seed=320)
    db.flush()
    before = {
        gp.team_id: (gp.style, gp.line_usage)
        for gp in db.query(TeamGameplan).all()
    }
    other = (
        db.query(Team).filter(Team.id != season.user_team_id).order_by(Team.id).first()
    )
    season.user_team_id = other.id
    db.flush()
    after = {
        gp.team_id: (gp.style, gp.line_usage)
        for gp in db.query(TeamGameplan).all()
    }
    assert before == after


def test_service_validation_directly(db):
    season = create_or_reset_league(db, seed=321)
    db.flush()
    with pytest.raises(GameplanInvalid):
        gameplan_service.update_user_team_gameplan(
            db, season.user_team_id, "kamikaze", "balanced"
        )
    with pytest.raises(TeamNotFound):
        gameplan_service.get_team_gameplan(db, 9999999)
    other = (
        db.query(Team).filter(Team.id != season.user_team_id).order_by(Team.id).first()
    )
    with pytest.raises(NotUserTeam):
        gameplan_service.update_user_team_gameplan(
            db, other.id, "offensive", "balanced"
        )
```

- [ ] **Step 2: Run the tests**

```bash
uv run pytest tests/test_gameplan_api.py -q
```

Expected: 9 passed.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_gameplan_api.py
git commit -m "feat(api): add gameplan API + service tests"
```

---

## Task 12: Frontend types and queries

**Files:** Modify `frontend/src/api/types.ts`. Create `frontend/src/queries/gameplan.ts`.

- [ ] **Step 1: Add types**

Append to `frontend/src/api/types.ts` (above the final `ApiError` export):

```ts
export type GameplanStyle = "balanced" | "offensive" | "defensive" | "physical";
export type GameplanLineUsage = "balanced" | "ride_top_lines" | "roll_all_lines";
export interface Gameplan {
  team_id: number;
  style: GameplanStyle;
  line_usage: GameplanLineUsage;
  editable: boolean;
}
```

- [ ] **Step 2: Add the queries**

`frontend/src/queries/gameplan.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Gameplan, GameplanLineUsage, GameplanStyle } from "../api/types";

export const useTeamGameplan = (teamId: number) =>
  useQuery({
    queryKey: ["team-gameplan", teamId],
    queryFn: () => api.get<Gameplan>(`/api/teams/${teamId}/gameplan`),
  });

export const useUpdateTeamGameplan = (teamId: number) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { style: GameplanStyle; line_usage: GameplanLineUsage }) =>
      api.put<Gameplan>(`/api/teams/${teamId}/gameplan`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["team-gameplan", teamId] });
      qc.invalidateQueries({ queryKey: ["schedule"] });
      qc.invalidateQueries({ queryKey: ["standings"] });
    },
  });
};
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/queries/gameplan.ts
git commit -m "feat(frontend): add Gameplan types and TanStack queries"
```

---

## Task 13: Frontend Gameplan card on team page

**Files:** Modify `frontend/src/routes/team.$teamId.tsx`.

- [ ] **Step 1: Inspect existing team page**

```bash
sed -n '1,40p' frontend/src/routes/team.\$teamId.tsx
```

Identify a logical place to add a new `<Card>` (near the bottom of the rendered tree, after the goalies card or similar).

- [ ] **Step 2: Add a `Gameplan` card**

Add to the file's imports (near the other `useQuery`/`useMutation` imports):

```ts
import { useState } from "react";
import { useTeamGameplan, useUpdateTeamGameplan } from "../queries/gameplan";
import type { GameplanLineUsage, GameplanStyle } from "../api/types";
```

Add this component above the route component:

```tsx
const GameplanCard = ({ teamId }: { teamId: number }) => {
  const q = useTeamGameplan(teamId);
  const m = useUpdateTeamGameplan(teamId);
  const [style, setStyle] = useState<GameplanStyle | null>(null);
  const [lineUsage, setLineUsage] = useState<GameplanLineUsage | null>(null);

  if (!q.data) return null;
  const gp = q.data;
  const currentStyle = style ?? gp.style;
  const currentLine = lineUsage ?? gp.line_usage;
  const dirty =
    currentStyle !== gp.style || currentLine !== gp.line_usage;

  if (!gp.editable) {
    return (
      <Card title="Gameplan" sub="Opponent personality">
        <div style={{ padding: "14px 16px", display: "flex", gap: 16 }}>
          <span className="chip">{gp.style}</span>
          <span className="chip">{gp.line_usage}</span>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Gameplan" sub="Applies to future games">
      <div style={{ padding: "14px 16px", display: "grid", gap: 10, gridTemplateColumns: "auto 1fr", alignItems: "center" }}>
        <label>Style</label>
        <select
          value={currentStyle}
          onChange={(e) => setStyle(e.target.value as GameplanStyle)}
        >
          {(["balanced", "offensive", "defensive", "physical"] as GameplanStyle[]).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <label>Line usage</label>
        <select
          value={currentLine}
          onChange={(e) => setLineUsage(e.target.value as GameplanLineUsage)}
        >
          {(["balanced", "ride_top_lines", "roll_all_lines"] as GameplanLineUsage[]).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <div />
        <button
          className="btn btn-primary"
          disabled={!dirty || m.isPending}
          onClick={() =>
            m.mutate(
              { style: currentStyle, line_usage: currentLine },
              { onSuccess: () => { setStyle(null); setLineUsage(null); } }
            )
          }
        >
          {m.isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </Card>
  );
};
```

(`Card` import is already in this file. If not, add `import { Card } from "../components/Card";`.)

Then in the rendered JSX, add `<GameplanCard teamId={id} />` after the existing roster cards (near the bottom, before `</Shell>`).

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build 2>&1 | tail -8
```

Expected: build succeeds, no TypeScript errors.

- [ ] **Step 4: Manually verify in browser**

Start the dev server (`cd frontend && npm run dev`) and the backend, then:
1. Navigate to your team page → see Gameplan card with two `<select>`s and Save button.
2. Change style/line_usage, click Save → toast/no error → reload page, change persists.
3. Navigate to a non-user team → see two read-only chips.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/team.\$teamId.tsx
git commit -m "feat(frontend): add Gameplan card to team page"
```

---

## Task 14: Final regression run

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && uv run pytest -q
```

Expected: all pass. Numbers: 94 (Phase 4 baseline) + 5 rotation-schedule + 8 gameplan-sim + 9 gameplan-api = ~116 tests.

- [ ] **Step 2: Smoke the user loop manually**

1. Reset the league.
2. On the user team page, change gameplan to `offensive`/`ride_top_lines`. Save.
3. Advance a few matchdays; verify games complete cleanly.
4. Open an opponent team page; verify gameplan chips render and are not editable.
5. Try `PUT` on a non-user team via curl/devtools; verify 403.
6. Check `/api/season/start-next` after season completes; gameplans for all teams unchanged afterwards.

- [ ] **Step 3: Final commit if cleanup needed**

```bash
git status
git add -p
git commit -m "fix: post-Phase-5A smoke cleanup"
```

---

## Self-Review

Spec coverage:
- ✅ `team_gameplan` table → Tasks 6, 7.
- ✅ CHECK constraints → Task 6 model + Task 7 migration.
- ✅ AI gameplan deterministic from league seed → Task 9 (`generate_gameplans_for_league`).
- ✅ User team defaults to balanced/balanced → Task 9 (`_current_user_team_id` branch in `generate_gameplans_for_league`).
- ✅ Rollover preserves gameplans → Task 11 has `test_rollover_preserves_gameplans`.
- ✅ `set_user_team` doesn't reset → Task 11 has `test_set_user_team_does_not_change_gameplans`.
- ✅ `SimGameplan` + `SimTeamInput` → Task 3.
- ✅ Constants in `sim/constants.py` → Task 1.
- ✅ Engine modifiers (shot prob, shot quality, suppression, penalties, line selection) → Task 4.
- ✅ Defensive suppression applied exactly once → Task 4 step 3 (in `_on_ice_attackers_and_def`).
- ✅ Shot-quality clamp/normalize → Task 4 step 4 (`SHOT_QUALITY_FLOOR`).
- ✅ Penalty averaging → Task 4 step 5.
- ✅ `build_rotation_schedule` → Task 2.
- ✅ Tests: determinism, offensive/defensive/physical effects, line-usage shifts, player quality dominance, schedule correctness → Task 5 + Task 2.
- ✅ Service validation, 403/404/422 mapping → Tasks 8, 9, 10, 11.
- ✅ API surface (`GET`/`PUT /api/teams/{id}/gameplan`) → Task 10.
- ✅ Frontend Gameplan card (read-only chips for non-user teams; selects + save for user team) → Task 13.

Type/method consistency: `SimGameplan(style, line_usage)` defined in Task 3 used identically in Tasks 4, 5, 9. `_style_mod` defined in Task 4 step 1 and used in steps 3–5. `build_rotation_schedule` defined in Task 2 and called in Task 4 step 7. Service function names (`get_team_gameplan`, `update_user_team_gameplan`, `is_editable`, `generate_gameplans_for_league`) match between Task 9 (definition) and Tasks 10, 11 (callers). `GameplanOut` / `UpdateGameplanIn` defined in Task 8 used in Task 10.

Placeholder scan: no "TBD"/"TODO"/"appropriate"/"similar to". Each step has full code or full command.

Plan complete and saved to `docs/superpowers/plans/2026-04-30-phase-5a-gameplan.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
