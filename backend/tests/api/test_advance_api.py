from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.services.generation.schedule import GAMES_PER_TEAM
from app.services.generation.teams import TEAM_COUNT

EXPECTED_MATCHDAYS = GAMES_PER_TEAM


def test_full_season_via_api(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)
        client.post("/api/league", json={"seed": 5})
        # Sim through regular season + playoffs.
        while True:
            r = client.post("/api/season/advance")
            assert r.status_code == 200
            if r.json()["season_status"] == "complete":
                break
        status = client.get("/api/season/status").json()
        assert status["status"] == "complete"
        standings = client.get("/api/standings").json()
        assert len(standings["rows"]) == TEAM_COUNT
        games = client.get("/api/schedule").json()["games"]
        rs_games = [g for g in games if g["matchday"] <= EXPECTED_MATCHDAYS]
        assert all(g["status"] == "simulated" for g in rs_games)
        playoffs = client.get("/api/playoffs").json()
        assert playoffs["champion_team_id"] is not None
        assert len(playoffs["rounds"]) == 4
        box = client.get(f"/api/games/{games[0]['id']}").json()
        assert box["events"]
    finally:
        app.dependency_overrides.clear()
