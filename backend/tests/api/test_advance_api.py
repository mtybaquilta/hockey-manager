from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.services.generation.schedule import GAMES_PER_PAIRING
from app.services.generation.teams import TEAM_COUNT

EXPECTED_MATCHDAYS = (TEAM_COUNT - 1) * GAMES_PER_PAIRING


def test_full_season_via_api(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)
        client.post("/api/league", json={"seed": 5})
        for _ in range(EXPECTED_MATCHDAYS):
            r = client.post("/api/season/advance")
            assert r.status_code == 200
        status = client.get("/api/season/status").json()
        assert status == {"current_matchday": EXPECTED_MATCHDAYS + 1, "status": "complete"}
        standings = client.get("/api/standings").json()
        assert len(standings["rows"]) == TEAM_COUNT
        games = client.get("/api/schedule").json()["games"]
        assert all(g["status"] == "simulated" for g in games)
        box = client.get(f"/api/games/{games[0]['id']}").json()
        assert box["events"]
    finally:
        app.dependency_overrides.clear()
