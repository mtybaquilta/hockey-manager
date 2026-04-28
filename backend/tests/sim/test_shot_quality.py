"""Shot quality is assigned to every shot/save and biased by strength."""
from collections import Counter

from sim.engine import simulate_game
from sim.models import EventKind, ShotQuality, SimGameInput, Strength

from tests.sim.test_engine_determinism import _team


def _events_over_seeds(n: int):
    out = []
    for seed in range(n):
        r = simulate_game(SimGameInput(home=_team(1000), away=_team(2000), seed=seed))
        out.extend(r.events)
    return out


def test_every_shot_has_a_quality():
    events = _events_over_seeds(20)
    for e in events:
        if e.kind in (EventKind.SAVE, EventKind.GOAL):
            assert e.shot_quality in set(ShotQuality)
        elif e.kind == EventKind.PENALTY:
            assert e.shot_quality is None


def test_quality_distribution_has_all_three_buckets():
    events = _events_over_seeds(40)
    qualities = [e.shot_quality for e in events if e.kind in (EventKind.SAVE, EventKind.GOAL)]
    counter = Counter(qualities)
    for q in ShotQuality:
        assert counter[q] > 0, f"bucket {q} never appeared"


def test_pp_shots_skew_toward_high_quality():
    events = _events_over_seeds(60)
    ev = [e for e in events if e.kind in (EventKind.SAVE, EventKind.GOAL) and e.strength == Strength.EV]
    pp = [e for e in events if e.kind in (EventKind.SAVE, EventKind.GOAL) and e.strength == Strength.PP]
    assert ev and pp
    ev_high = sum(1 for e in ev if e.shot_quality == ShotQuality.HIGH) / len(ev)
    pp_high = sum(1 for e in pp if e.shot_quality == ShotQuality.HIGH) / len(pp)
    assert pp_high > ev_high, f"PP HIGH share {pp_high:.2f} not above EV HIGH share {ev_high:.2f}"


def test_sh_shots_skew_toward_low_quality():
    events = _events_over_seeds(300)
    ev = [e for e in events if e.kind in (EventKind.SAVE, EventKind.GOAL) and e.strength == Strength.EV]
    sh = [e for e in events if e.kind in (EventKind.SAVE, EventKind.GOAL) and e.strength == Strength.SH]
    assert ev and sh, "need sample of EV and SH shots"
    ev_low = sum(1 for e in ev if e.shot_quality == ShotQuality.LOW) / len(ev)
    sh_low = sum(1 for e in sh if e.shot_quality == ShotQuality.LOW) / len(sh)
    assert sh_low > ev_low, f"SH LOW share {sh_low:.2f} not above EV LOW share {ev_low:.2f}"


def test_quality_assignment_is_deterministic():
    a = simulate_game(SimGameInput(home=_team(1000), away=_team(2000), seed=99))
    b = simulate_game(SimGameInput(home=_team(1000), away=_team(2000), seed=99))
    a_q = [e.shot_quality for e in a.events]
    b_q = [e.shot_quality for e in b.events]
    assert a_q == b_q
