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


def test_value_skater_returns_int(db):
    from app.services.league_service import create_or_reset_league
    from app.models import Skater, Team
    from app.services.trade_eval import value_skater

    create_or_reset_league(db, seed=42)
    teams = db.query(Team).order_by(Team.id).all()
    src = teams[0]
    dst = teams[1]
    s = db.query(Skater).filter(Skater.team_id == src.id).first()
    v = value_skater(db, s, receiving_team_id=dst.id, season_year=_season_year(db))
    assert isinstance(v, int)


def _season_year(db):
    from app.models import Season
    return db.query(Season).order_by(Season.id.desc()).first().year


def test_value_goalie_returns_int(db):
    from app.services.league_service import create_or_reset_league
    from app.models import Goalie, Team
    from app.services.trade_eval import value_goalie

    create_or_reset_league(db, seed=42)
    teams = db.query(Team).order_by(Team.id).all()
    g = db.query(Goalie).filter(Goalie.team_id == teams[0].id).first()
    v = value_goalie(db, g, receiving_team_id=teams[1].id, season_year=_season_year(db))
    assert isinstance(v, int)


def test_evaluate_offer_rejects_partner_equals_user(db):
    import pytest
    from app.services.league_service import create_or_reset_league
    from app.services import manager_profile_service, trade_service
    from app.services.trade_eval import OfferPlayer
    from app.services.trade_service import TradeWithOwnTeamNotAllowed
    from app.models import Skater, Team

    create_or_reset_league(db, seed=42)
    p = manager_profile_service.create_profile(db, name="Coach")
    t = db.query(Team).order_by(Team.id).first()
    manager_profile_service.set_team(db, p.id, t.id)
    db.flush()
    s1, s2 = db.query(Skater).filter(Skater.team_id == t.id).limit(2).all()
    with pytest.raises(TradeWithOwnTeamNotAllowed):
        trade_service.evaluate_offer(
            db,
            partner_team_id=t.id,
            offered=[OfferPlayer("skater", s1.id)],
            requested=[OfferPlayer("skater", s2.id)],
        )
