import pytest

from app.errors import LeagueNotFound, TeamNotFound
from app.models import Game, Standing, Team
from app.services.generation.schedule import GAMES_PER_TEAM
from app.services.generation.teams import TEAM_COUNT
from app.services.league_service import create_or_reset_league, get_league, set_user_team

EXPECTED_GAMES = TEAM_COUNT * GAMES_PER_TEAM // 2


def test_create_league_full_setup(db):
    s = create_or_reset_league(db, seed=42)
    assert s.id is not None
    assert s.user_team_id is not None
    assert db.query(Team).count() == TEAM_COUNT
    assert db.query(Game).count() == EXPECTED_GAMES
    assert db.query(Standing).count() == TEAM_COUNT


def test_get_league_raises_when_empty(db):
    with pytest.raises(LeagueNotFound):
        get_league(db)


def test_create_resets_existing(db):
    create_or_reset_league(db, seed=1)
    create_or_reset_league(db, seed=2)
    assert db.query(Team).count() == TEAM_COUNT


def test_set_user_team_validates(db):
    create_or_reset_league(db, seed=1)
    with pytest.raises(TeamNotFound):
        set_user_team(db, team_id=99999)
