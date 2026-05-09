# backend/tests/test_contract_generation.py
import random
from collections import Counter

from app.models import Contract, Goalie, Skater
from app.services.generation.contracts import generate_initial_contracts


def test_every_rostered_player_has_active_contract(db_with_league):
    db = db_with_league
    skaters = db.query(Skater).filter(Skater.team_id.is_not(None)).all()
    goalies = db.query(Goalie).filter(Goalie.team_id.is_not(None)).all()
    contracts_by_skater = {c.skater_id for c in db.query(Contract).filter_by(status="active").all() if c.skater_id is not None}
    contracts_by_goalie = {c.goalie_id for c in db.query(Contract).filter_by(status="active").all() if c.goalie_id is not None}
    for s in skaters:
        assert s.id in contracts_by_skater, f"skater {s.id} has no active contract"
    for g in goalies:
        assert g.id in contracts_by_goalie


def test_free_agents_have_no_contract(db_with_league):
    db = db_with_league
    fa_skaters = db.query(Skater).filter(Skater.team_id.is_(None)).all()
    for s in fa_skaters:
        c = db.query(Contract).filter_by(skater_id=s.id, status="active").one_or_none()
        assert c is None


def test_lengths_distributed(db_with_league):
    db = db_with_league
    contracts = db.query(Contract).filter_by(status="active").all()
    counts = Counter(c.length for c in contracts)
    # Sanity: all weighted lengths are present and 2y is the modal weight.
    for length in [1, 2, 3, 4, 5]:
        assert counts[length] > 0
    assert counts[2] >= counts[1]  # 2y is heavier-weighted than 1y


def test_expiry_years_staggered(db_with_league):
    db = db_with_league
    contracts = db.query(Contract).filter_by(status="active").all()
    counts = Counter(c.expires_after_year for c in contracts)
    most_common_count = counts.most_common(1)[0][1]
    assert most_common_count <= len(contracts) * 0.5


def test_deterministic_from_seed(db_factory):
    # Two leagues with the same seed produce the same contracts.
    db1 = db_factory(seed=42)
    db2 = db_factory(seed=42)

    def _row(c):
        # Use -1 sentinel for None so tuples are sortable.
        return (c.skater_id or -1, c.goalie_id or -1, c.length, c.salary, c.expires_after_year, c.signed_season_year)

    cs1 = sorted([_row(c) for c in db1.query(Contract).all()])
    cs2 = sorted([_row(c) for c in db2.query(Contract).all()])
    assert cs1 == cs2
