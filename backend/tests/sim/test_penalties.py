from sim.engine import PENALTY_DURATION_TICKS, simulate_game
from sim.models import EventKind, SimGameInput, Strength

from tests.sim.test_engine_determinism import _team


def _run(seed: int):
    return simulate_game(SimGameInput(home=_team(1000), away=_team(2000), seed=seed))


def test_penalties_are_deterministic():
    a = _run(123)
    b = _run(123)
    a_pens = [e for e in a.events if e.kind == EventKind.PENALTY]
    b_pens = [e for e in b.events if e.kind == EventKind.PENALTY]
    assert a_pens == b_pens


def test_penalty_duration_is_set():
    r = _run(7)
    for e in r.events:
        if e.kind == EventKind.PENALTY:
            assert e.penalty_duration_ticks == PENALTY_DURATION_TICKS


def test_penalty_count_is_reasonable_over_many_seeds():
    """Penalties happen, but not absurdly often. Soft range check."""
    counts = []
    for seed in range(20):
        r = _run(seed)
        counts.append(sum(1 for e in r.events if e.kind == EventKind.PENALTY))
    avg = sum(counts) / len(counts)
    # PENALTY_PER_TICK_PROB ≈ 0.012 over ~180 ticks => ~2.2 expected
    assert 0.5 <= avg <= 6.0, f"avg penalties/game = {avg}"


def test_pp_goal_only_when_opp_in_box():
    """PP-tagged goals must occur during a tick where the opposing team has at least one
    active penalty that started before or at the goal tick and is still serving."""
    r = _run(31)
    pens_by_team_home = sorted(
        (e.tick, e.tick + (e.penalty_duration_ticks or 0))
        for e in r.events
        if e.kind == EventKind.PENALTY and e.team_is_home
    )
    pens_by_team_away = sorted(
        (e.tick, e.tick + (e.penalty_duration_ticks or 0))
        for e in r.events
        if e.kind == EventKind.PENALTY and not e.team_is_home
    )

    def opp_active(tick: int, opp_pens: list[tuple[int, int]]) -> bool:
        # Opposing team is in the box if any penalty's window covers `tick`.
        # Penalties are added at their tick and tick down, so the offender serves
        # ticks (start, start + duration]. The PP team scores during that span.
        return any(start < tick <= start + (end - start) for start, end in opp_pens)

    for e in r.events:
        if e.kind == EventKind.GOAL and e.strength == Strength.PP:
            opp = pens_by_team_home if not e.team_is_home else pens_by_team_away
            assert opp_active(e.tick, opp), f"PP goal at tick {e.tick} with no opp penalty"


def test_sh_goal_only_when_own_team_in_box():
    r = _run(58)
    pens_home = sorted(
        (e.tick, e.tick + (e.penalty_duration_ticks or 0))
        for e in r.events
        if e.kind == EventKind.PENALTY and e.team_is_home
    )
    pens_away = sorted(
        (e.tick, e.tick + (e.penalty_duration_ticks or 0))
        for e in r.events
        if e.kind == EventKind.PENALTY and not e.team_is_home
    )

    for e in r.events:
        if e.kind == EventKind.GOAL and e.strength == Strength.SH:
            own = pens_home if e.team_is_home else pens_away
            assert any(start < e.tick <= end for start, end in own), (
                f"SH goal at tick {e.tick} with no own-team penalty"
            )
