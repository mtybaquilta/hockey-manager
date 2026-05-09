from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.services.generation.teams import TEAM_COUNT


def test_post_get_league_flow(db):
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
        # No manager profile yet, so league has no user team set.
        assert body["user_team_id"] is None

        # Create a manager profile and assign a team via /manager-profile.
        rm = client.post("/api/manager-profile", json={"name": "Coach"})
        assert rm.status_code == 200
        target = body["teams"][2]["id"]
        rt = client.put("/api/manager-profile/team", json={"team_id": target})
        assert rt.status_code == 200
        assert rt.json()["current_team_id"] == target
        assert client.get("/api/league").json()["user_team_id"] == target
    finally:
        app.dependency_overrides.clear()
