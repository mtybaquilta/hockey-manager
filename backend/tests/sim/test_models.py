import pytest

from sim.models import (
    Position,
    SimGoalie,
    SimLine,
    SimSkater,
    SimTeamLineup,
)


def test_skater_is_frozen():
    s = SimSkater(id=1, position=Position.C, skating=80, shooting=80, passing=80, defense=70, physical=60)
    with pytest.raises(Exception):
        s.skating = 99  # type: ignore[misc]


def test_team_lineup_has_4_lines_3_pairs():
    f = lambda i: SimSkater(id=i, position=Position.C, skating=70, shooting=70, passing=70, defense=70, physical=70)
    d = lambda i: SimSkater(id=i, position=Position.LD, skating=70, shooting=70, passing=70, defense=70, physical=70)
    g = SimGoalie(id=99, reflexes=80, positioning=80, rebound_control=70, puck_handling=60, mental=70)
    lu = SimTeamLineup(
        forward_lines=tuple(SimLine(skaters=(f(i * 3), f(i * 3 + 1), f(i * 3 + 2))) for i in range(4)),
        defense_pairs=tuple(SimLine(skaters=(d(100 + i * 2), d(101 + i * 2))) for i in range(3)),
        starting_goalie=g,
    )
    assert len(lu.forward_lines) == 4
    assert len(lu.defense_pairs) == 3
