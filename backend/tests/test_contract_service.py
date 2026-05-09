from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Contract, Goalie, Skater, Team
from app.services import contract_service


def _make_skater(db, *, team_id=None):
    sk = Skater(
        team_id=team_id, name="Test", birth_date=date(2000, 1, 1), position="C",
        skating=70, shooting=70, passing=70, defense=60, physical=70,
        potential=80, development_type="steady",
    )
    db.add(sk)
    db.flush()
    return sk


def test_get_active_contract_skater_none(db):
    sk = _make_skater(db)
    assert contract_service.get_active_contract_for_skater(db, sk.id) is None


def test_create_active_contract_then_get(db):
    sk = _make_skater(db)
    c = contract_service.create_contract_for_skater(
        db, sk.id, length=2, signed_season_year=2025, salary=1500, no_trade_clause=False,
    )
    fetched = contract_service.get_active_contract_for_skater(db, sk.id)
    assert fetched is not None
    assert fetched.id == c.id
    assert c.expires_after_year == 2026


def test_partial_unique_index_blocks_two_actives(db):
    sk = _make_skater(db)
    contract_service.create_contract_for_skater(db, sk.id, length=2, signed_season_year=2025, salary=1500)
    db.commit()
    with pytest.raises(IntegrityError):
        contract_service.create_contract_for_skater(db, sk.id, length=1, signed_season_year=2025, salary=1500)
        db.commit()


def test_terminate_contract_flips_status_and_year(db):
    sk = _make_skater(db)
    c = contract_service.create_contract_for_skater(db, sk.id, length=3, signed_season_year=2025, salary=1500)
    contract_service.terminate_contract(db, c, season_year=2026)
    db.refresh(c)
    assert c.status == "terminated"
    assert c.terminated_season_year == 2026


def test_terminate_non_active_raises(db):
    sk = _make_skater(db)
    c = contract_service.create_contract_for_skater(db, sk.id, length=3, signed_season_year=2025, salary=1500)
    contract_service.terminate_contract(db, c, season_year=2026)
    with pytest.raises(contract_service.ContractStateError):
        contract_service.terminate_contract(db, c, season_year=2027)


def test_expire_contracts_for_year(db):
    sk_keep = _make_skater(db)
    sk_exp = _make_skater(db)
    contract_service.create_contract_for_skater(db, sk_keep.id, length=3, signed_season_year=2025, salary=1500)
    contract_service.create_contract_for_skater(db, sk_exp.id, length=1, signed_season_year=2025, salary=1500)
    expired = contract_service.expire_contracts_through_year(db, new_season_year=2026)
    assert expired == [("skater", sk_exp.id)]
    assert contract_service.get_active_contract_for_skater(db, sk_keep.id) is not None
    assert contract_service.get_active_contract_for_skater(db, sk_exp.id) is None
