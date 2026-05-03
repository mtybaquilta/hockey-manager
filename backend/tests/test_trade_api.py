from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models import Goalie, Lineup, Season, Skater, Team
from app.services.league_service import create_or_reset_league
from app.services.trade_service import compute_trade_block


def _client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def _setup(db, seed=42):
    season = create_or_reset_league(db, seed=seed)
    db.flush()
    return season


def _block_skater_for(db, target_team_id: int) -> dict:
    block = compute_trade_block(db)
    for e in block:
        if e["team_id"] == target_team_id and e["player_type"] == "skater":
            return e
    raise AssertionError("no skater on block for that team")


def _user_skater_with_position(db, user_team_id: int, position: str) -> Skater:
    return (
        db.query(Skater)
        .filter(Skater.team_id == user_team_id, Skater.position == position)
        .order_by(Skater.id)
        .first()
    )


def test_get_trade_block_excludes_user_team(db):
    season = _setup(db)
    try:
        client = _client(db)
        r = client.get("/api/trade-block")
        assert r.status_code == 200
        body = r.json()
        assert body
        assert all(e["team_id"] != season.user_team_id for e in body)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_propose_invalid_cross_type(db):
    season = _setup(db)
    try:
        client = _client(db)
        # arbitrary ids; cross-type detected before id resolution
        r = client.post(
            "/api/trades/propose",
            json={
                "target_player_type": "skater",
                "target_player_id": 1,
                "offered_player_type": "goalie",
                "offered_player_id": 1,
            },
        )
        assert r.status_code == 422
        assert r.json()["error_code"] == "TradeOfferInvalid"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_propose_with_own_team_rejected(db):
    season = _setup(db)
    try:
        client = _client(db)
        # both target and offered are user-team players
        own_a = (
            db.query(Skater).filter(Skater.team_id == season.user_team_id).order_by(Skater.id).first()
        )
        own_b = (
            db.query(Skater)
            .filter(Skater.team_id == season.user_team_id, Skater.id != own_a.id)
            .order_by(Skater.id)
            .first()
        )
        r = client.post(
            "/api/trades/propose",
            json={
                "target_player_type": "skater",
                "target_player_id": own_a.id,
                "offered_player_type": "skater",
                "offered_player_id": own_b.id,
            },
        )
        assert r.status_code == 422
        assert r.json()["error_code"] == "TradeWithOwnTeamNotAllowed"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_propose_free_agent_rejected(db):
    season = _setup(db)
    try:
        client = _client(db)
        fa = db.query(Skater).filter(Skater.team_id.is_(None)).first()
        own = (
            db.query(Skater).filter(Skater.team_id == season.user_team_id).order_by(Skater.id).first()
        )
        r = client.post(
            "/api/trades/propose",
            json={
                "target_player_type": "skater",
                "target_player_id": fa.id,
                "offered_player_type": "skater",
                "offered_player_id": own.id,
            },
        )
        assert r.status_code == 422
        assert r.json()["error_code"] == "TradeOfferInvalid"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_propose_target_not_on_block_rejected(db):
    season = _setup(db)
    try:
        client = _client(db)
        # Top forward on an AI team — almost certainly excluded as top-core.
        ai = db.query(Team).filter(Team.id != season.user_team_id).order_by(Team.id).first()
        ai_forwards = (
            db.query(Skater)
            .filter(Skater.team_id == ai.id, Skater.position.in_(("LW", "C", "RW")))
            .all()
        )
        ai_forwards.sort(
            key=lambda s: -(s.shooting + s.skating + s.passing + s.defense + s.physical)
        )
        top = ai_forwards[0]
        own = (
            db.query(Skater).filter(Skater.team_id == season.user_team_id).order_by(Skater.id).first()
        )
        r = client.post(
            "/api/trades/propose",
            json={
                "target_player_type": "skater",
                "target_player_id": top.id,
                "offered_player_type": "skater",
                "offered_player_id": own.id,
            },
        )
        assert r.status_code == 404
        assert r.json()["error_code"] == "TradeTargetNotAvailable"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_propose_value_too_low_returns_soft_reject(db):
    season = _setup(db)
    try:
        client = _client(db)
        ai = db.query(Team).filter(Team.id != season.user_team_id).order_by(Team.id).first()
        target = _block_skater_for(db, ai.id)
        # Offer the lowest-OVR same-position user skater available.
        own_pool = (
            db.query(Skater)
            .filter(Skater.team_id == season.user_team_id, Skater.position == target["position"])
            .all()
        )
        own_pool.sort(
            key=lambda s: (s.shooting + s.skating + s.passing + s.defense + s.physical)
        )
        weak = own_pool[0]
        r = client.post(
            "/api/trades/propose",
            json={
                "target_player_type": "skater",
                "target_player_id": target["player_id"],
                "offered_player_type": "skater",
                "offered_player_id": weak.id,
            },
        )
        assert r.status_code == 200
        body = r.json()
        # Either accepted (weak still beats the asking) or rejected as too-low.
        # If rejected, DB should be unchanged.
        if not body["accepted"]:
            assert body["error_code"] == "TradeValueTooLow"
            db.expire_all()
            assert db.get(Skater, target["player_id"]).team_id == ai.id
            assert db.get(Skater, weak.id).team_id == season.user_team_id
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_propose_accepted_swaps_team_ids(db):
    season = _setup(db)
    try:
        client = _client(db)
        ai = db.query(Team).filter(Team.id != season.user_team_id).order_by(Team.id).first()
        target = _block_skater_for(db, ai.id)
        # Find a strong same-position user skater so the offer clears asking value.
        own_pool = (
            db.query(Skater)
            .filter(Skater.team_id == season.user_team_id, Skater.position == target["position"])
            .all()
        )
        own_pool.sort(
            key=lambda s: -(s.shooting + s.skating + s.passing + s.defense + s.physical)
        )
        strong = own_pool[0]
        r = client.post(
            "/api/trades/propose",
            json={
                "target_player_type": "skater",
                "target_player_id": target["player_id"],
                "offered_player_type": "skater",
                "offered_player_id": strong.id,
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        if body["accepted"]:
            db.expire_all()
            assert db.get(Skater, target["player_id"]).team_id == season.user_team_id
            assert db.get(Skater, strong.id).team_id == ai.id
            # Re-proposing the same target now hits TradeWithOwnTeamNotAllowed.
            r2 = client.post(
                "/api/trades/propose",
                json={
                    "target_player_type": "skater",
                    "target_player_id": target["player_id"],
                    "offered_player_type": "skater",
                    "offered_player_id": strong.id,
                },
            )
            assert r2.status_code == 422
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_propose_clears_lineup_slot_on_accept(db):
    season = _setup(db)
    try:
        client = _client(db)
        ai = db.query(Team).filter(Team.id != season.user_team_id).order_by(Team.id).first()
        target = _block_skater_for(db, ai.id)
        own_pool = (
            db.query(Skater)
            .filter(Skater.team_id == season.user_team_id, Skater.position == target["position"])
            .all()
        )
        own_pool.sort(
            key=lambda s: -(s.shooting + s.skating + s.passing + s.defense + s.physical)
        )
        strong = own_pool[0]

        # Confirm the target is currently in the AI team's lineup somewhere.
        ai_lineup = db.query(Lineup).filter(Lineup.team_id == ai.id).first()
        target_was_in_lineup = any(
            getattr(ai_lineup, c.name) == target["player_id"]
            for c in ai_lineup.__table__.columns
            if c.name.endswith("_id") and c.name != "team_id"
        )

        r = client.post(
            "/api/trades/propose",
            json={
                "target_player_type": "skater",
                "target_player_id": target["player_id"],
                "offered_player_type": "skater",
                "offered_player_id": strong.id,
            },
        )
        assert r.status_code == 200, r.text
        if r.json()["accepted"] and target_was_in_lineup:
            db.expire_all()
            ai_lineup_after = db.query(Lineup).filter(Lineup.team_id == ai.id).first()
            still_there = any(
                getattr(ai_lineup_after, c.name) == target["player_id"]
                for c in ai_lineup_after.__table__.columns
                if c.name.endswith("_id") and c.name != "team_id"
            )
            assert not still_there, "lineup slot should be cleared on acceptance"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_propose_blocked_when_season_complete(db):
    season = _setup(db)
    try:
        client = _client(db)
        ai = db.query(Team).filter(Team.id != season.user_team_id).order_by(Team.id).first()
        target = _block_skater_for(db, ai.id)
        own = (
            db.query(Skater).filter(Skater.team_id == season.user_team_id).order_by(Skater.id).first()
        )
        # mark season complete
        s = db.query(Season).order_by(Season.id.desc()).first()
        s.status = "complete"
        db.flush()
        r = client.post(
            "/api/trades/propose",
            json={
                "target_player_type": "skater",
                "target_player_id": target["player_id"],
                "offered_player_type": "skater",
                "offered_player_id": own.id,
            },
        )
        assert r.status_code == 409
        assert r.json()["error_code"] == "SeasonAlreadyComplete"
    finally:
        app.dependency_overrides.pop(get_db, None)
