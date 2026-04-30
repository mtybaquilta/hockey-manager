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
    """Smoke: offensive vs defensive run for many seeds without crashing."""
    for s in range(30):
        simulate_game(_input(s, SimGameplan("offensive", "balanced"), SimGameplan("defensive", "balanced")))
