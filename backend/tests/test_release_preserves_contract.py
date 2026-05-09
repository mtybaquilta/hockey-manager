from app.models import Contract, Season, Skater
from app.services import contract_service, free_agents_service


def test_release_skater_terminates_contract(db_with_league):
    db = db_with_league
    season = db.query(Season).order_by(Season.id.desc()).first()
    sk = db.query(Skater).filter(Skater.team_id == season.user_team_id).first()
    active = contract_service.get_active_contract_for_skater(db, sk.id)
    assert active is not None

    free_agents_service.release_skater(db, season.user_team_id, sk.id)

    db.refresh(active)
    assert active.status == "terminated"
    assert active.terminated_season_year is not None
    assert sk.team_id is None
    assert contract_service.get_active_contract_for_skater(db, sk.id) is None
    assert db.query(Contract).filter_by(id=active.id).one_or_none() is not None
