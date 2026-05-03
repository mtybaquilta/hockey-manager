from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.services.generation.schedule import GAMES_PER_TEAM

EXPECTED_MATCHDAYS = GAMES_PER_TEAM


def test_stats_and_player_detail(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)
        client.post("/api/league", json={"seed": 9})
        for _ in range(EXPECTED_MATCHDAYS):
            client.post("/api/season/advance")

        skaters = client.get("/api/stats/skaters").json()["rows"]
        assert skaters
        assert all("points" in r and "shooting_pct" in r for r in skaters)
        assert skaters == sorted(skaters, key=lambda r: (-r["points"], -r["goals"], r["name"]))

        goalies = client.get("/api/stats/goalies").json()["rows"]
        assert goalies
        assert all("save_pct" in r for r in goalies)

        teams = client.get("/api/stats/teams").json()["rows"]
        assert len(teams) == TEAM_COUNT
        assert all(0.0 <= r["pp_pct"] <= 1.0 for r in teams)
        assert all(0.0 <= r["pk_pct"] <= 1.0 for r in teams)

        sk_id = skaters[0]["skater_id"]
        detail = client.get(f"/api/players/skater/{sk_id}").json()
        assert detail["totals"]["points"] == skaters[0]["points"]
        assert len(detail["game_log"]) == detail["totals"]["games_played"]

        gk_id = goalies[0]["goalie_id"]
        gdetail = client.get(f"/api/players/goalie/{gk_id}").json()
        assert gdetail["totals"]["games_played"] == len(gdetail["game_log"])

        assert client.get("/api/players/skater/9999999").status_code == 404
        assert client.get("/api/players/goalie/9999999").status_code == 404
    finally:
        app.dependency_overrides.clear()
