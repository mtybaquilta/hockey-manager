import pytest

from app.errors import SeasonAlreadyComplete
from app.models import Game, Season, Standing
from app.services.advance_service import advance_matchday
from app.services.league_service import create_or_reset_league


def test_advance_one_matchday(db):
    create_or_reset_league(db, seed=1)
    res = advance_matchday(db)
    assert len(res["advanced_game_ids"]) == 2
    assert res["current_matchday"] == 2
    sims = db.query(Game).filter_by(status="simulated").count()
    assert sims == 2
    points_total = sum(s.points for s in db.query(Standing).all())
    assert points_total in {4, 5, 6}


def test_full_season_runs_to_complete(db):
    create_or_reset_league(db, seed=2)
    for _ in range(9):
        advance_matchday(db)
    season = db.query(Season).one()
    assert season.status == "complete"
    assert db.query(Game).filter_by(status="simulated").count() == 18
    with pytest.raises(SeasonAlreadyComplete):
        advance_matchday(db)


def test_standings_consistency(db):
    create_or_reset_league(db, seed=3)
    for _ in range(9):
        advance_matchday(db)
    standings = db.query(Standing).all()
    for s in standings:
        assert s.games_played == s.wins + s.losses + s.ot_losses
        assert s.points == 2 * s.wins + s.ot_losses
