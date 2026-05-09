from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models import Season, Skater
from app.services import contract_service, trade_service


def _client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def test_trade_block_excludes_ntc_holders(db_with_league):
    db = db_with_league
    season = db.query(Season).order_by(Season.id.desc()).first()
    sk = (
        db.query(Skater)
        .filter(Skater.team_id.is_not(None), Skater.team_id != season.user_team_id)
        .first()
    )
    c = contract_service.get_active_contract_for_skater(db, sk.id)
    assert c is not None
    c.no_trade_clause = True
    db.flush()
    block = trade_service.compute_trade_block(db)
    for entry in block:
        assert not (entry["player_type"] == "skater" and entry["player_id"] == sk.id)


def test_propose_trade_rejected_for_ntc(db_with_league):
    db = db_with_league
    season = db.query(Season).order_by(Season.id.desc()).first()
    user_team_id = season.user_team_id

    # Find a target on another team eligible for the trade block.
    block = trade_service.compute_trade_block(db)
    target = next(e for e in block if e["player_type"] == "skater")

    # Find an offered skater on the user team with the same position.
    offered = (
        db.query(Skater)
        .filter(Skater.team_id == user_team_id, Skater.position == target["position"])
        .first()
    )
    assert offered is not None

    # Flip NTC on the target.
    target_contract = contract_service.get_active_contract_for_skater(db, target["player_id"])
    target_contract.no_trade_clause = True
    db.flush()

    try:
        client = _client(db)
        res = client.post(
            "/api/trades/propose",
            json={
                "target_player_type": "skater",
                "target_player_id": target["player_id"],
                "offered_player_type": "skater",
                "offered_player_id": offered.id,
            },
        )
        assert res.status_code == 409
        assert res.json()["error_code"] == "NoTradeClause"
    finally:
        app.dependency_overrides.pop(get_db, None)
