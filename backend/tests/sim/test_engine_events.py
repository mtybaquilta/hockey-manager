from sim.engine import simulate_game
from sim.models import EventKind, ResultType, SimGameInput

from tests.sim.test_engine_determinism import _team


def test_goal_count_matches_score():
    inp = SimGameInput(home=_team(1000), away=_team(2000), seed=7)
    r = simulate_game(inp)
    home_goals = sum(1 for e in r.events if e.kind == EventKind.GOAL and e.team_is_home)
    away_goals = sum(1 for e in r.events if e.kind == EventKind.GOAL and not e.team_is_home)
    if r.result_type == ResultType.SO:
        assert abs(home_goals - away_goals) <= 1
        assert abs(r.home_score - r.away_score) == 1
    else:
        assert (home_goals, away_goals) == (r.home_score, r.away_score)


def test_shot_count_matches():
    inp = SimGameInput(home=_team(1000), away=_team(2000), seed=11)
    r = simulate_game(inp)
    home_shots = sum(1 for e in r.events if e.kind in (EventKind.SAVE, EventKind.GOAL) and e.team_is_home)
    away_shots = sum(1 for e in r.events if e.kind in (EventKind.SAVE, EventKind.GOAL) and not e.team_is_home)
    assert r.home_shots == home_shots
    assert r.away_shots == away_shots


def test_skater_stat_aggregation():
    r = simulate_game(SimGameInput(home=_team(1000), away=_team(2000), seed=3))
    goal_events = [e for e in r.events if e.kind == EventKind.GOAL]
    total_goals = sum(s.goals for s in r.skater_stats)
    assert total_goals == len(goal_events)
