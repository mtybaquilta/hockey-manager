import pytest

from app.errors import LineupIncomplete
from app.models import Lineup
from app.services import manager_profile_service
from app.services.advance_service import advance_matchday


def test_advance_blocked_when_user_lineup_has_empty_slot(db_with_league):
    db = db_with_league
    user_team_id = manager_profile_service.current_team_id(db)
    lu = db.query(Lineup).filter_by(team_id=user_team_id).one()
    lu.line1_lw_id = None
    db.flush()
    with pytest.raises(LineupIncomplete) as ei:
        advance_matchday(db)
    assert "line1_lw_id" in ei.value.message


def test_advance_passes_when_lineup_complete(db_with_league):
    db = db_with_league
    res = advance_matchday(db)
    assert "season_phase" in res
