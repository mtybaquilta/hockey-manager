from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.services.generation.teams import TEAM_COUNT


def test_post_get_put_league_flow(db):
    def _override():
        yield db
    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)
        assert client.get("/api/league").status_code == 404
        r = client.post("/api/league", json={"seed": 7})
        assert r.status_code == 200
        body = r.json()
        assert len(body["teams"]) == TEAM_COUNT
        assert body["user_team_id"] == body["teams"][0]["id"]
        new_team = body["teams"][2]["id"]
        r2 = client.put("/api/league/user-team", json={"team_id": new_team})
        assert r2.json()["user_team_id"] == new_team
    finally:
        app.dependency_overrides.clear()
