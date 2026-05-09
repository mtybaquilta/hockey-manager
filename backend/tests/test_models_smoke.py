from app.models import Season, Team


def test_can_create_season_and_team(db):
    s = Season(seed=42, year=2025)
    db.add(s)
    db.flush()
    t = Team(name="Test FC", abbreviation="TFC")
    db.add(t)
    db.flush()
    assert t.id is not None


def test_season_has_year(db):
    from app.models import Season

    s = Season(seed=1, current_matchday=1, status="active", phase="regular_season", year=2026)
    db.add(s)
    db.flush()
    fetched = db.query(Season).filter_by(id=s.id).one()
    assert fetched.year == 2026
