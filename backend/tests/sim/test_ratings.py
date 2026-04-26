from sim.models import Position, SimGoalie, SimLine, SimSkater
from sim.ratings import goalie_save_rating, line_offense, pair_defense


def _f(i, sh=70, pa=70, sk=70, de=60, ph=60):
    return SimSkater(id=i, position=Position.C, skating=sk, shooting=sh, passing=pa, defense=de, physical=ph)


def test_line_offense_uses_shooting_passing_skating():
    line = SimLine(skaters=(_f(1, sh=90), _f(2, sh=70), _f(3, sh=50)))
    val = line_offense(line)
    assert 0 < val < 100


def test_pair_defense_average():
    pair = SimLine(skaters=(_f(1, de=80), _f(2, de=60)))
    assert pair_defense(pair) == 70


def test_goalie_save_rating_combines_attrs():
    g = SimGoalie(id=1, reflexes=90, positioning=80, rebound_control=70, puck_handling=60, mental=70)
    assert 70 <= goalie_save_rating(g) <= 90
