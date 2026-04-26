from sim.engine import simulate_game
from sim.models import (
    Position,
    SimGameInput,
    SimGoalie,
    SimLine,
    SimSkater,
    SimTeamLineup,
)


def _team(off_id_base: int) -> SimTeamLineup:
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
    return SimTeamLineup(forward_lines=forward_lines, defense_pairs=pairs, starting_goalie=g)


def test_same_seed_same_result():
    inp = SimGameInput(home=_team(1000), away=_team(2000), seed=42)
    a = simulate_game(inp)
    b = simulate_game(inp)
    assert a == b


def test_different_seed_different_result():
    a = simulate_game(SimGameInput(home=_team(1000), away=_team(2000), seed=1))
    b = simulate_game(SimGameInput(home=_team(1000), away=_team(2000), seed=2))
    assert (a.home_score, a.away_score) != (b.home_score, b.away_score) or a.events != b.events
