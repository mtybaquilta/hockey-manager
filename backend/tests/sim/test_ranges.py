"""Soft range checks: the engine should produce roughly hockey-like averages."""
from sim.engine import simulate_game
from sim.models import SimGameInput

from tests.sim.test_engine_determinism import _team


def _avg_over_seeds(n: int):
    shots, goals = [], []
    for seed in range(n):
        r = simulate_game(SimGameInput(home=_team(1000), away=_team(2000), seed=seed))
        shots.append(r.home_shots + r.away_shots)
        goals.append(r.home_score + r.away_score)
    return sum(shots) / n, sum(goals) / n


def test_average_shots_in_sensible_range():
    avg_shots, _ = _avg_over_seeds(30)
    assert 40 <= avg_shots <= 80, f"avg total shots/game = {avg_shots}"


def test_average_goals_in_sensible_range():
    _, avg_goals = _avg_over_seeds(30)
    assert 3.0 <= avg_goals <= 9.0, f"avg total goals/game = {avg_goals}"
