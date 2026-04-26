from sim.engine import simulate_game
from sim.models import ResultType, SimGameInput

from tests.sim.test_engine_determinism import _team


def test_eventually_produces_each_result_type():
    seen: set[ResultType] = set()
    for seed in range(0, 1000):
        r = simulate_game(SimGameInput(home=_team(1000), away=_team(2000), seed=seed))
        seen.add(r.result_type)
        if seen == {ResultType.REG, ResultType.OT, ResultType.SO}:
            return
    raise AssertionError(f"missing result types after 1000 seeds: {seen}")


def test_ot_result_has_one_goal_diff():
    for seed in range(0, 1000):
        r = simulate_game(SimGameInput(home=_team(1000), away=_team(2000), seed=seed))
        if r.result_type == ResultType.OT:
            assert abs(r.home_score - r.away_score) == 1
            return
    raise AssertionError("no OT game produced in 1000 seeds")
