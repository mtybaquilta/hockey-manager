import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.errors import GameplanInvalid, NotUserTeam, TeamNotFound
from app.main import app
from app.models import Team, TeamGameplan
from app.services import gameplan_service, season_rollover_service
from app.services.advance_service import advance_matchday
from app.services.league_service import create_or_reset_league


def test_league_creation_seeds_gameplans(db):
    season = create_or_reset_league(db, seed=314)
    db.flush()
    team_count = db.query(Team).count()
    gp_count = db.query(TeamGameplan).count()
    assert gp_count == team_count
    user_gp = (
        db.query(TeamGameplan).filter_by(team_id=season.user_team_id).one()
    )
    assert user_gp.style == "balanced"
    assert user_gp.line_usage == "balanced"


def test_get_gameplan_marks_editable_correctly(db):
    season = create_or_reset_league(db, seed=315)
    db.flush()

    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)
        r = client.get(f"/api/teams/{season.user_team_id}/gameplan")
        assert r.status_code == 200
        assert r.json()["editable"] is True
        other = (
            db.query(Team).filter(Team.id != season.user_team_id).order_by(Team.id).first()
        )
        r = client.get(f"/api/teams/{other.id}/gameplan")
        assert r.status_code == 200
        assert r.json()["editable"] is False
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_put_gameplan_user_team_persists(db):
    season = create_or_reset_league(db, seed=316)
    db.flush()

    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)
        r = client.put(
            f"/api/teams/{season.user_team_id}/gameplan",
            json={"style": "offensive", "line_usage": "ride_top_lines"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["style"] == "offensive"
        assert body["line_usage"] == "ride_top_lines"
        gp = (
            db.query(TeamGameplan).filter_by(team_id=season.user_team_id).one()
        )
        assert gp.style == "offensive"
        assert gp.line_usage == "ride_top_lines"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_put_gameplan_on_non_user_team_returns_403(db):
    season = create_or_reset_league(db, seed=317)
    db.flush()
    other = (
        db.query(Team).filter(Team.id != season.user_team_id).order_by(Team.id).first()
    )

    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)
        r = client.put(
            f"/api/teams/{other.id}/gameplan",
            json={"style": "offensive", "line_usage": "balanced"},
        )
        assert r.status_code == 403
        assert r.json()["error_code"] == "NotUserTeam"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_put_gameplan_invalid_style_returns_422(db):
    season = create_or_reset_league(db, seed=318)
    db.flush()

    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)
        r = client.put(
            f"/api/teams/{season.user_team_id}/gameplan",
            json={"style": "kamikaze", "line_usage": "balanced"},
        )
        assert r.status_code == 422
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_get_gameplan_unknown_team_returns_404(db):
    create_or_reset_league(db, seed=319)
    db.flush()

    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)
        r = client.get("/api/teams/9999999/gameplan")
        assert r.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_rollover_preserves_gameplans(db):
    season = create_or_reset_league(db, seed=2026)
    db.flush()
    before = {
        gp.team_id: (gp.style, gp.line_usage)
        for gp in db.query(TeamGameplan).all()
    }
    while advance_matchday(db)["season_status"] != "complete":
        pass
    db.commit()
    season_rollover_service.start_next_season(db)
    db.commit()
    after = {
        gp.team_id: (gp.style, gp.line_usage)
        for gp in db.query(TeamGameplan).all()
    }
    assert before == after


def test_set_user_team_does_not_change_gameplans(db):
    season = create_or_reset_league(db, seed=320)
    db.flush()
    before = {
        gp.team_id: (gp.style, gp.line_usage)
        for gp in db.query(TeamGameplan).all()
    }
    other = (
        db.query(Team).filter(Team.id != season.user_team_id).order_by(Team.id).first()
    )
    season.user_team_id = other.id
    db.flush()
    after = {
        gp.team_id: (gp.style, gp.line_usage)
        for gp in db.query(TeamGameplan).all()
    }
    assert before == after


def test_service_validation_directly(db):
    season = create_or_reset_league(db, seed=321)
    db.flush()
    with pytest.raises(GameplanInvalid):
        gameplan_service.update_user_team_gameplan(
            db, season.user_team_id, "kamikaze", "balanced"
        )
    with pytest.raises(TeamNotFound):
        gameplan_service.get_team_gameplan(db, 9999999)
    other = (
        db.query(Team).filter(Team.id != season.user_team_id).order_by(Team.id).first()
    )
    with pytest.raises(NotUserTeam):
        gameplan_service.update_user_team_gameplan(
            db, other.id, "offensive", "balanced"
        )
