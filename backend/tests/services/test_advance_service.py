import pytest

from app.errors import SeasonAlreadyComplete
from app.models import Game, Season, Standing
from app.services.advance_service import advance_matchday
from app.services.generation.schedule import GAMES_PER_TEAM
from app.services.generation.teams import TEAM_COUNT
from app.services.league_service import create_or_reset_league

MATCHDAYS = GAMES_PER_TEAM
GAMES_PER_MATCHDAY = TEAM_COUNT // 2
TOTAL_GAMES = TEAM_COUNT * GAMES_PER_TEAM // 2


def test_advance_one_matchday(db):
    create_or_reset_league(db, seed=1)
    res = advance_matchday(db)
    assert len(res["advanced_game_ids"]) == GAMES_PER_MATCHDAY
    assert res["current_matchday"] == 2
    assert db.query(Game).filter_by(status="simulated").count() == GAMES_PER_MATCHDAY
    # Each game distributes 2 points (REG) or 3 points (OT/SO).
    points_total = sum(s.points for s in db.query(Standing).all())
    assert 2 * GAMES_PER_MATCHDAY <= points_total <= 3 * GAMES_PER_MATCHDAY


def test_full_season_runs_to_complete(db):
    create_or_reset_league(db, seed=2)
    for _ in range(MATCHDAYS):
        advance_matchday(db)
    season = db.query(Season).one()
    assert season.status == "complete"
    assert db.query(Game).filter_by(status="simulated").count() == TOTAL_GAMES
    with pytest.raises(SeasonAlreadyComplete):
        advance_matchday(db)


def test_standings_consistency(db):
    create_or_reset_league(db, seed=3)
    for _ in range(MATCHDAYS):
        advance_matchday(db)
    standings = db.query(Standing).all()
    for s in standings:
        assert s.games_played == s.wins + s.losses + s.ot_losses
        assert s.points == 2 * s.wins + s.ot_losses
