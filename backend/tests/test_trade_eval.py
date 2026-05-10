from app.services.trade_eval import age_modifier, potential_modifier, classify_team_role, contender_modifier


def test_age_modifier_brackets():
    assert age_modifier(20) == 4
    assert age_modifier(25) == 2
    assert age_modifier(29) == 0
    assert age_modifier(33) == -2
    assert age_modifier(36) == -5


def test_potential_modifier_young_high_potential():
    assert potential_modifier(potential=92, age=21) == 6
    assert potential_modifier(potential=86, age=22) == 4
    assert potential_modifier(potential=86, age=25) == 2
    assert potential_modifier(potential=78, age=31) == -1
    assert potential_modifier(potential=80, age=27) == 0


def test_contender_modifier_values_present_skill():
    assert contender_modifier("contender", age=27) == 1
    assert contender_modifier("contender", age=34) == -2
    assert contender_modifier("rebuilder", age=22) == 2
    assert contender_modifier("rebuilder", age=31) == -2
    assert contender_modifier("middle", age=27) == 0


def test_classify_team_role_uses_avg_skater_ovr(db):
    from app.services.league_service import create_or_reset_league
    from app.models import Team
    create_or_reset_league(db, seed=42)
    team_id = db.query(Team).order_by(Team.id).first().id
    role = classify_team_role(db, team_id)
    assert role in ("contender", "middle", "rebuilder")
