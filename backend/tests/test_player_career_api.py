from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models import Skater, SkaterGameStat
from app.services import season_rollover_service
from app.services.advance_service import advance_matchday
from app.services.league_service import create_or_reset_league


def _play_through(db) -> None:
    while advance_matchday(db)["season_status"] != "complete":
        pass


def test_career_spans_two_seasons(db):
    create_or_reset_league(db, seed=314)
    db.flush()
    _play_through(db)
    season_rollover_service.start_next_season(db)
    db.flush()
    _play_through(db)

    skater = (
        db.query(Skater, SkaterGameStat)
        .join(SkaterGameStat, SkaterGameStat.skater_id == Skater.id)
        .first()[0]
    )
    raw_g = sum(
        r.goals for r in db.query(SkaterGameStat).filter_by(skater_id=skater.id).all()
    )

    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)
        r = client.get(f"/api/players/skater/{skater.id}/career")
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["by_season"]) >= 2
        assert body["totals"]["g"] == raw_g
        assert body["totals"]["gp"] == sum(s["gp"] for s in body["by_season"])
    finally:
        app.dependency_overrides.pop(get_db, None)
