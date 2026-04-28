from sim.models import Position, SimGoalie, SimLine, SimSkater, SimTeamLineup
from sim.special_teams import (
    pk_score,
    pk_unit_defense,
    pp_score,
    pp_unit_offense,
    select_special_teams,
)


def _skater(id_: int, pos: Position, sh=70, pa=70, sk=70, de=70, ph=70) -> SimSkater:
    return SimSkater(id=id_, position=pos, skating=sk, shooting=sh, passing=pa, defense=de, physical=ph)


def _team_with_specialists() -> SimTeamLineup:
    """Lineup where a couple of skaters are clearly best for PP and others for PK."""
    pp_star_lw = _skater(1, Position.LW, sh=95, pa=95, sk=90, de=40, ph=40)
    pp_star_c = _skater(2, Position.C, sh=92, pa=98, sk=88, de=45, ph=45)
    pp_star_rw = _skater(3, Position.RW, sh=94, pa=88, sk=92, de=40, ph=40)
    pk_star_c = _skater(4, Position.C, sh=55, pa=55, sk=82, de=88, ph=88)
    pk_star_lw = _skater(5, Position.LW, sh=50, pa=50, sk=80, de=85, ph=90)

    lines = [
        SimLine(skaters=(pp_star_lw, pp_star_c, pp_star_rw)),
        SimLine(skaters=(pk_star_lw, pk_star_c, _skater(6, Position.RW))),
        SimLine(skaters=(_skater(7, Position.LW), _skater(8, Position.C), _skater(9, Position.RW))),
        SimLine(skaters=(_skater(10, Position.LW), _skater(11, Position.C), _skater(12, Position.RW))),
    ]

    pp_d_a = _skater(20, Position.LD, sh=80, pa=85, sk=85, de=70, ph=60)
    pp_d_b = _skater(21, Position.RD, sh=82, pa=80, sk=82, de=68, ph=60)
    pk_d_a = _skater(22, Position.LD, sh=50, pa=50, sk=80, de=90, ph=85)
    pk_d_b = _skater(23, Position.RD, sh=50, pa=50, sk=78, de=88, ph=88)

    pairs = (
        SimLine(skaters=(pp_d_a, pp_d_b)),
        SimLine(skaters=(pk_d_a, pk_d_b)),
        SimLine(skaters=(_skater(24, Position.LD), _skater(25, Position.RD))),
    )
    g = SimGoalie(id=99, reflexes=80, positioning=80, rebound_control=70, puck_handling=60, mental=70)
    return SimTeamLineup(forward_lines=tuple(lines), defense_pairs=pairs, starting_goalie=g)


def test_pp_unit_has_three_forwards_and_two_defense():
    st = select_special_teams(_team_with_specialists())
    assert len(st.pp_forwards) == 3
    assert len(st.pp_defense) == 2
    assert all(s.position in {Position.LW, Position.C, Position.RW} for s in st.pp_forwards)
    assert all(s.position in {Position.LD, Position.RD} for s in st.pp_defense)


def test_pk_unit_has_two_forwards_and_two_defense():
    st = select_special_teams(_team_with_specialists())
    assert len(st.pk_forwards) == 2
    assert len(st.pk_defense) == 2


def test_pp_unit_picks_high_shooting_passing_skating_skaters():
    team = _team_with_specialists()
    st = select_special_teams(team)
    selected_ids = {s.id for s in st.pp_forwards} | {s.id for s in st.pp_defense}
    # Hand-tuned PP stars
    assert {1, 2, 3, 20, 21}.issubset(selected_ids)


def test_pk_unit_picks_high_defense_skating_physical_skaters():
    team = _team_with_specialists()
    st = select_special_teams(team)
    selected_ids = {s.id for s in st.pk_forwards} | {s.id for s in st.pk_defense}
    assert {4, 5, 22, 23}.issubset(selected_ids)


def test_selection_is_deterministic():
    team = _team_with_specialists()
    a = select_special_teams(team)
    b = select_special_teams(team)
    assert a == b


def test_pp_offense_is_higher_than_pk_offense():
    team = _team_with_specialists()
    st = select_special_teams(team)
    pp_units = (*st.pp_forwards, *st.pp_defense)
    pk_units = (*st.pk_forwards, *st.pk_defense)
    assert sum(pp_score(s) for s in pp_units) > sum(pp_score(s) for s in pk_units)


def test_pk_defense_is_higher_than_pp_defense():
    team = _team_with_specialists()
    st = select_special_teams(team)
    pp_units = (*st.pp_forwards, *st.pp_defense)
    pk_units = (*st.pk_forwards, *st.pk_defense)
    assert sum(pk_score(s) for s in pk_units) > sum(pk_score(s) for s in pp_units)


def test_unit_rating_helpers_return_floats():
    st = select_special_teams(_team_with_specialists())
    assert isinstance(pp_unit_offense(st), float)
    assert isinstance(pk_unit_defense(st), float)
