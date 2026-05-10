from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models import Goalie, Lineup, Season, Skater, Team
from app.services import manager_profile_service
from app.services.league_service import create_or_reset_league


def _client(db):
    def _override():
        yield db
    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def _setup(db, seed=42):
    create_or_reset_league(db, seed=seed)
    p = manager_profile_service.create_profile(db, name="Coach")
    t = db.query(Team).order_by(Team.id).first()
    manager_profile_service.set_team(db, p.id, t.id)
    db.flush()
    return t


def test_evaluate_returns_outlook(db):
    user_t = _setup(db)
    try:
        client = _client(db)
        ai = db.query(Team).filter(Team.id != user_t.id).order_by(Team.id).first()
        own = db.query(Skater).filter(Skater.team_id == user_t.id).first()
        target = db.query(Skater).filter(Skater.team_id == ai.id).first()
        r = client.post("/api/trades/evaluate", json={
            "partner_team_id": ai.id,
            "offered": [{"player_type": "skater", "player_id": own.id}],
            "requested": [{"player_type": "skater", "player_id": target.id}],
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["outlook"] in ("accept", "close", "reject")
        assert "offered_value" in body and "requested_value" in body
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_execute_swaps_team_ids_when_accepted(db):
    user_t = _setup(db)
    try:
        client = _client(db)
        ai = db.query(Team).filter(Team.id != user_t.id).order_by(Team.id).first()
        ai_skaters = db.query(Skater).filter(Skater.team_id == ai.id).all()
        ai_skaters.sort(key=lambda s: s.shooting + s.skating + s.passing + s.defense + s.physical)
        target = ai_skaters[0]
        own_pool = db.query(Skater).filter(
            Skater.team_id == user_t.id, Skater.position == target.position
        ).all()
        own_pool.sort(key=lambda s: -(s.shooting + s.skating + s.passing + s.defense + s.physical))
        offered = own_pool[0]
        r = client.post("/api/trades/execute", json={
            "partner_team_id": ai.id,
            "offered": [{"player_type": "skater", "player_id": offered.id}],
            "requested": [{"player_type": "skater", "player_id": target.id}],
        })
        assert r.status_code == 200, r.text
        body = r.json()
        if body["accepted"]:
            db.expire_all()
            assert db.get(Skater, target.id).team_id == user_t.id
            assert db.get(Skater, offered.id).team_id == ai.id
            assert {(a["player_type"], a["player_id"]) for a in body["acquired"]} == {("skater", target.id)}
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_execute_does_not_mutate_when_rejected(db):
    user_t = _setup(db)
    try:
        client = _client(db)
        ai = db.query(Team).filter(Team.id != user_t.id).order_by(Team.id).first()
        ai_skaters = db.query(Skater).filter(Skater.team_id == ai.id).all()
        ai_skaters.sort(key=lambda s: -(s.shooting + s.skating + s.passing + s.defense + s.physical))
        target = ai_skaters[0]
        own_pool = db.query(Skater).filter(
            Skater.team_id == user_t.id, Skater.position == target.position
        ).all()
        own_pool.sort(key=lambda s: s.shooting + s.skating + s.passing + s.defense + s.physical)
        weak = own_pool[0]
        r = client.post("/api/trades/execute", json={
            "partner_team_id": ai.id,
            "offered": [{"player_type": "skater", "player_id": weak.id}],
            "requested": [{"player_type": "skater", "player_id": target.id}],
        })
        assert r.status_code == 200
        body = r.json()
        if not body["accepted"]:
            db.expire_all()
            assert db.get(Skater, target.id).team_id == ai.id
            assert db.get(Skater, weak.id).team_id == user_t.id
            assert body["acquired"] == []
            assert body["traded_away"] == []
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_evaluate_partner_eq_user_team_rejected(db):
    user_t = _setup(db)
    try:
        client = _client(db)
        s1, s2 = db.query(Skater).filter(Skater.team_id == user_t.id).limit(2).all()
        r = client.post("/api/trades/evaluate", json={
            "partner_team_id": user_t.id,
            "offered": [{"player_type": "skater", "player_id": s1.id}],
            "requested": [{"player_type": "skater", "player_id": s2.id}],
        })
        assert r.status_code == 422
        assert r.json()["error_code"] == "TradeWithOwnTeamNotAllowed"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_evaluate_blocked_when_season_complete(db):
    user_t = _setup(db)
    try:
        client = _client(db)
        ai = db.query(Team).filter(Team.id != user_t.id).order_by(Team.id).first()
        own = db.query(Skater).filter(Skater.team_id == user_t.id).first()
        target = db.query(Skater).filter(Skater.team_id == ai.id).first()
        s = db.query(Season).order_by(Season.id.desc()).first()
        s.status = "complete"
        db.flush()
        r = client.post("/api/trades/evaluate", json={
            "partner_team_id": ai.id,
            "offered": [{"player_type": "skater", "player_id": own.id}],
            "requested": [{"player_type": "skater", "player_id": target.id}],
        })
        assert r.status_code == 409
        assert r.json()["error_code"] == "SeasonAlreadyComplete"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_execute_clears_lineup_slots(db):
    user_t = _setup(db)
    try:
        client = _client(db)
        ai = db.query(Team).filter(Team.id != user_t.id).order_by(Team.id).first()
        ai_skaters = db.query(Skater).filter(Skater.team_id == ai.id).all()
        ai_skaters.sort(key=lambda s: s.shooting + s.skating + s.passing + s.defense + s.physical)
        target = ai_skaters[0]
        own_pool = db.query(Skater).filter(
            Skater.team_id == user_t.id, Skater.position == target.position
        ).all()
        own_pool.sort(key=lambda s: -(s.shooting + s.skating + s.passing + s.defense + s.physical))
        offered = own_pool[0]
        r = client.post("/api/trades/execute", json={
            "partner_team_id": ai.id,
            "offered": [{"player_type": "skater", "player_id": offered.id}],
            "requested": [{"player_type": "skater", "player_id": target.id}],
        })
        if r.json().get("accepted"):
            db.expire_all()
            ai_lu = db.query(Lineup).filter(Lineup.team_id == ai.id).first()
            user_lu = db.query(Lineup).filter(Lineup.team_id == user_t.id).first()
            cols = [c.name for c in ai_lu.__table__.columns if c.name.endswith("_id") and c.name != "team_id"]
            assert all(getattr(ai_lu, c) != target.id for c in cols)
            assert all(getattr(user_lu, c) != offered.id for c in cols)
    finally:
        app.dependency_overrides.pop(get_db, None)
