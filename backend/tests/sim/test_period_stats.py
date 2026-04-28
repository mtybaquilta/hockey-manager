from sim.engine import simulate_game
from sim.models import EventKind, ResultType, SimGameInput

from tests.sim.test_engine_determinism import _team


def test_period_breakdown_sums_to_totals():
    r = simulate_game(SimGameInput(home=_team(1000), away=_team(2000), seed=21))
    assert sum(r.home_shots_by_period) == r.home_shots
    assert sum(r.away_shots_by_period) == r.away_shots

    home_goal_events = sum(1 for e in r.events if e.kind == EventKind.GOAL and e.team_is_home)
    away_goal_events = sum(1 for e in r.events if e.kind == EventKind.GOAL and not e.team_is_home)
    assert sum(r.home_goals_by_period) == home_goal_events
    assert sum(r.away_goals_by_period) == away_goal_events


def test_period_breakdown_has_four_buckets():
    r = simulate_game(SimGameInput(home=_team(1000), away=_team(2000), seed=22))
    assert len(r.home_goals_by_period) == 4
    assert len(r.away_goals_by_period) == 4
    assert len(r.home_shots_by_period) == 4
    assert len(r.away_shots_by_period) == 4


def test_no_overtime_means_empty_ot_bucket():
    # Find a seed that finishes in regulation; assert OT bucket is zero.
    for seed in range(1, 60):
        r = simulate_game(SimGameInput(home=_team(1000), away=_team(2000), seed=seed))
        if r.result_type == ResultType.REG:
            assert r.home_goals_by_period[3] == 0
            assert r.away_goals_by_period[3] == 0
            assert r.home_shots_by_period[3] == 0
            assert r.away_shots_by_period[3] == 0
            return
    raise AssertionError("no regulation result found in seed range")
