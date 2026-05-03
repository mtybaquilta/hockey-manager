from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models import Goalie, Lineup, Skater, Team
from app.services.league_service import create_or_reset_league


def _client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def _setup(db, seed=42):
    season = create_or_reset_league(db, seed=seed)
    db.flush()
    return season


def _any_fa_skater(db) -> Skater:
    return db.query(Skater).filter(Skater.team_id.is_(None)).first()


def _any_fa_goalie(db) -> Goalie:
    return db.query(Goalie).filter(Goalie.team_id.is_(None)).first()


def test_sign_skater_attaches_to_user_team(db):
    season = _setup(db)
    try:
        client = _client(db)
        sk = _any_fa_skater(db)
        r = client.post(f"/api/teams/{season.user_team_id}/sign/skater/{sk.id}")
        assert r.status_code == 200, r.text
        assert r.json()["team_id"] == season.user_team_id
        db.expire_all()
        assert db.get(Skater, sk.id).team_id == season.user_team_id
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_sign_rejected_for_non_user_team(db):
    season = _setup(db)
    try:
        client = _client(db)
        other = (
            db.query(Team).filter(Team.id != season.user_team_id).order_by(Team.id).first()
        )
        sk = _any_fa_skater(db)
        r = client.post(f"/api/teams/{other.id}/sign/skater/{sk.id}")
        assert r.status_code == 403
        assert r.json()["error_code"] == "NotUserTeam"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_sign_rejected_when_already_signed(db):
    season = _setup(db)
    try:
        client = _client(db)
        rostered = db.query(Skater).filter(Skater.team_id.is_not(None)).first()
        r = client.post(
            f"/api/teams/{season.user_team_id}/sign/skater/{rostered.id}"
        )
        assert r.status_code == 400
        assert r.json()["error_code"] == "PlayerNotFreeAgent"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_sign_goalie(db):
    season = _setup(db)
    try:
        client = _client(db)
        g = _any_fa_goalie(db)
        r = client.post(f"/api/teams/{season.user_team_id}/sign/goalie/{g.id}")
        assert r.status_code == 200
        assert r.json()["team_id"] == season.user_team_id
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_release_clears_lineup_slots(db):
    season = _setup(db)
    try:
        client = _client(db)
        lu = db.query(Lineup).filter_by(team_id=season.user_team_id).first()
        skater_id = lu.line1_c_id
        assert skater_id is not None

        r = client.post(
            f"/api/teams/{season.user_team_id}/release/skater/{skater_id}"
        )
        assert r.status_code == 200, r.text
        assert r.json()["team_id"] is None

        db.expire_all()
        lu2 = db.query(Lineup).filter_by(team_id=season.user_team_id).first()
        assert lu2.line1_c_id is None
        assert db.get(Skater, skater_id).team_id is None
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_release_rejected_for_non_user_team(db):
    season = _setup(db)
    try:
        client = _client(db)
        other = (
            db.query(Team).filter(Team.id != season.user_team_id).order_by(Team.id).first()
        )
        other_skater = db.query(Skater).filter(Skater.team_id == other.id).first()
        r = client.post(f"/api/teams/{other.id}/release/skater/{other_skater.id}")
        assert r.status_code == 403
        assert r.json()["error_code"] == "NotUserTeam"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_release_rejected_when_player_not_on_team(db):
    season = _setup(db)
    try:
        client = _client(db)
        other = (
            db.query(Team).filter(Team.id != season.user_team_id).order_by(Team.id).first()
        )
        other_skater = db.query(Skater).filter(Skater.team_id == other.id).first()
        r = client.post(
            f"/api/teams/{season.user_team_id}/release/skater/{other_skater.id}"
        )
        assert r.status_code == 400
        assert r.json()["error_code"] == "PlayerNotOnTeam"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_release_then_resign_keeps_id(db):
    season = _setup(db)
    try:
        client = _client(db)
        lu = db.query(Lineup).filter_by(team_id=season.user_team_id).first()
        sk_id = lu.line2_lw_id
        rel = client.post(
            f"/api/teams/{season.user_team_id}/release/skater/{sk_id}"
        )
        assert rel.status_code == 200
        re_sign = client.post(
            f"/api/teams/{season.user_team_id}/sign/skater/{sk_id}"
        )
        assert re_sign.status_code == 200
        body = re_sign.json()
        assert body["id"] == sk_id
        assert body["team_id"] == season.user_team_id
    finally:
        app.dependency_overrides.pop(get_db, None)
