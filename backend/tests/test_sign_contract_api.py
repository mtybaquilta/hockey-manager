from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models import Season, Skater
from app.services import manager_profile_service


def _client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def _user_team_id(db) -> int:
    return manager_profile_service.current_team_id(db)


def test_sign_skater_with_terms(db_with_league):
    db = db_with_league
    try:
        client = _client(db)
        team_id = _user_team_id(db)
        fa = db.query(Skater).filter(Skater.team_id.is_(None)).first()
        body = {"length": 3, "salary": 2000, "no_trade_clause": True}
        res = client.post(f"/api/teams/{team_id}/sign/skater/{fa.id}", json=body)
        assert res.status_code == 200, res.text
        payload = res.json()
        assert payload["team_id"] == team_id
        assert payload["contract"]["length"] == 3
        assert payload["contract"]["salary"] == 2000
        assert payload["contract"]["no_trade_clause"] is True
        assert payload["contract"]["status"] == "active"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_sign_skater_invalid_length(db_with_league):
    db = db_with_league
    try:
        client = _client(db)
        team_id = _user_team_id(db)
        fa = db.query(Skater).filter(Skater.team_id.is_(None)).first()
        res = client.post(
            f"/api/teams/{team_id}/sign/skater/{fa.id}",
            json={"length": 0, "salary": 2000},
        )
        assert res.status_code == 422
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_sign_skater_invalid_salary(db_with_league):
    db = db_with_league
    try:
        client = _client(db)
        team_id = _user_team_id(db)
        fa = db.query(Skater).filter(Skater.team_id.is_(None)).first()
        res = client.post(
            f"/api/teams/{team_id}/sign/skater/{fa.id}",
            json={"length": 2, "salary": 100},
        )
        assert res.status_code == 422
    finally:
        app.dependency_overrides.pop(get_db, None)
