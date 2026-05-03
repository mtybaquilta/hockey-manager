from app.models import Goalie, Skater
from app.services.league_service import create_or_reset_league


def test_league_creation_seeds_free_agent_pool(db):
    create_or_reset_league(db, seed=42)
    db.flush()
    fa_skaters = db.query(Skater).filter(Skater.team_id.is_(None)).count()
    fa_goalies = db.query(Goalie).filter(Goalie.team_id.is_(None)).count()
    assert fa_skaters == 40
    assert fa_goalies == 5


def test_rostered_players_have_team_after_creation(db):
    create_or_reset_league(db, seed=42)
    db.flush()
    rostered_skaters = db.query(Skater).filter(Skater.team_id.is_not(None)).count()
    rostered_goalies = db.query(Goalie).filter(Goalie.team_id.is_not(None)).count()
    assert rostered_skaters > 0
    assert rostered_goalies > 0
