import pytest

from app.errors import LineupInvalid, LineupSlotConflict
from app.models import Lineup, Skater, Team
from app.schemas.lineup import LineupSlots
from app.services.league_service import create_or_reset_league
from app.services.lineup_service import update_lineup


def _slots_from(lu: Lineup) -> LineupSlots:
    return LineupSlots(
        **{c.name: getattr(lu, c.name) for c in lu.__table__.columns if c.name not in ("id", "team_id")}
    )


def test_update_accepts_default(db):
    season = create_or_reset_league(db, seed=1)
    team_id = season.user_team_id
    lu = db.query(Lineup).filter_by(team_id=team_id).one()
    update_lineup(db, team_id, _slots_from(lu))


def test_duplicate_skater_rejected(db):
    season = create_or_reset_league(db, seed=1)
    team_id = season.user_team_id
    lu = db.query(Lineup).filter_by(team_id=team_id).one()
    s = _slots_from(lu).model_copy(update={"line2_c_id": lu.line1_c_id})
    with pytest.raises(LineupSlotConflict):
        update_lineup(db, team_id, s)


def test_wrong_position_rejected(db):
    season = create_or_reset_league(db, seed=1)
    team_id = season.user_team_id
    lu = db.query(Lineup).filter_by(team_id=team_id).one()
    # Swap an LW slot with a C — both end up in the wrong position slot, no duplicates.
    s = _slots_from(lu).model_copy(update={
        "line1_lw_id": lu.line1_c_id,
        "line1_c_id": lu.line1_lw_id,
    })
    with pytest.raises(LineupInvalid):
        update_lineup(db, team_id, s)


def test_other_team_skater_rejected(db):
    season = create_or_reset_league(db, seed=1)
    teams = db.query(Team).all()
    other_team = next(t for t in teams if t.id != season.user_team_id)
    other_lw = db.query(Skater).filter_by(team_id=other_team.id, position="LW").first()
    lu = db.query(Lineup).filter_by(team_id=season.user_team_id).one()
    s = _slots_from(lu).model_copy(update={"line1_lw_id": other_lw.id})
    with pytest.raises(LineupInvalid):
        update_lineup(db, season.user_team_id, s)
