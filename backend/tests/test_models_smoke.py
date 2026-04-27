from app.models import Season, Team


def test_can_create_season_and_team(db):
    s = Season(seed=42)
    db.add(s)
    db.flush()
    t = Team(season_id=s.id, name="Test FC", abbreviation="TFC")
    db.add(t)
    db.flush()
    assert t.id is not None
