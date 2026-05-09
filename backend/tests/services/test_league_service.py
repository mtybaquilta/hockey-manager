import pytest

from app.errors import LeagueNotFound, TeamNotFound
from app.models import Game, Standing, Team
from app.services import manager_profile_service
from app.services.generation.schedule import GAMES_PER_TEAM
from app.services.generation.teams import TEAM_COUNT
from app.services.league_service import create_or_reset_league, get_league

EXPECTED_GAMES = TEAM_COUNT * GAMES_PER_TEAM // 2


def test_create_league_full_setup(db):
    s = create_or_reset_league(db, seed=42)
    assert s.id is not None
    assert db.query(Team).count() == TEAM_COUNT
    assert db.query(Game).count() == EXPECTED_GAMES
    assert db.query(Standing).count() == TEAM_COUNT


def test_get_league_raises_when_empty(db):
    from app.models import Season

    db.query(Season).delete()
    db.flush()
    with pytest.raises(LeagueNotFound):
        get_league(db)


def test_create_resets_existing(db):
    create_or_reset_league(db, seed=1)
    create_or_reset_league(db, seed=2)
    assert db.query(Team).count() == TEAM_COUNT


def test_manager_set_team_validates(db):
    create_or_reset_league(db, seed=1)
    p = manager_profile_service.create_profile(db, name="Coach")
    with pytest.raises(TeamNotFound):
        manager_profile_service.set_team(db, p.id, team_id=99999)
