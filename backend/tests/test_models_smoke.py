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


def test_contract_model_basic(db):
    from datetime import date
    from app.models import Contract, Skater, Team

    team = Team(name="Smoke", abbreviation="SMK")
    db.add(team)
    db.flush()
    sk = Skater(
        team_id=team.id, name="Smoke Player",
        birth_date=date(2000, 1, 1), position="C",
        skating=70, shooting=70, passing=70, defense=60, physical=70,
        potential=80, development_type="steady",
    )
    db.add(sk)
    db.flush()
    c = Contract(
        skater_id=sk.id, length=3, signed_season_year=2025,
        expires_after_year=2027, salary=2000, status="active",
    )
    db.add(c)
    db.flush()
    assert c.id is not None
    assert c.status == "active"
