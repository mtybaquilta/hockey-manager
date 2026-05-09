from app.models import Season
from app.services.advance_service import advance_matchday


def test_playoffs_end_transitions_to_offseason(db_with_league):
    db = db_with_league
    for _ in range(5000):
        res = advance_matchday(db)
        if res["season_phase"] == "offseason":
            break
        if res["season_status"] == "complete":
            break
    season = db.query(Season).order_by(Season.id.desc()).first()
    assert season.phase == "offseason"
    assert season.status == "active"
    assert season.champion_team_id is not None
