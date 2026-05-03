import random
from collections import Counter

from app.models import Goalie, Skater
from app.services.generation.free_agents import generate_free_agent_pool
from app.services.generation.players import skater_overall


def test_generates_expected_counts(db):
    generate_free_agent_pool(random.Random(42), db, set())
    db.flush()
    skaters = db.query(Skater).filter(Skater.team_id.is_(None)).all()
    goalies = db.query(Goalie).filter(Goalie.team_id.is_(None)).all()
    assert len(skaters) == 40
    assert len(goalies) == 5


def test_position_distribution(db):
    generate_free_agent_pool(random.Random(42), db, set())
    db.flush()
    counts = Counter(
        s.position for s in db.query(Skater).filter(Skater.team_id.is_(None)).all()
    )
    assert counts == {"LW": 8, "C": 8, "RW": 8, "LD": 8, "RD": 8}


def test_pool_is_deterministic(db):
    generate_free_agent_pool(random.Random(99), db, set())
    db.flush()
    snap1 = sorted(
        (s.name, s.position, s.skating, s.shooting, s.passing, s.defense, s.physical)
        for s in db.query(Skater).filter(Skater.team_id.is_(None)).all()
    )
    # Wipe and regenerate inside the same outer transaction.
    db.query(Skater).filter(Skater.team_id.is_(None)).delete(synchronize_session=False)
    db.query(Goalie).filter(Goalie.team_id.is_(None)).delete(synchronize_session=False)
    db.flush()
    generate_free_agent_pool(random.Random(99), db, set())
    db.flush()
    snap2 = sorted(
        (s.name, s.position, s.skating, s.shooting, s.passing, s.defense, s.physical)
        for s in db.query(Skater).filter(Skater.team_id.is_(None)).all()
    )
    assert snap1 == snap2


def test_pool_includes_a_gem(db):
    generate_free_agent_pool(random.Random(7), db, set())
    db.flush()
    skaters = db.query(Skater).filter(Skater.team_id.is_(None)).all()
    overalls = [
        skater_overall(s.skating, s.shooting, s.passing, s.defense, s.physical)
        for s in skaters
    ]
    assert max(overalls) >= 75


def test_no_name_collision_with_used(db):
    forbidden = {"Alice Free", "Bob Pool"}
    used = set(forbidden)
    generate_free_agent_pool(random.Random(5), db, used)
    db.flush()
    names = {s.name for s in db.query(Skater).filter(Skater.team_id.is_(None)).all()}
    names |= {g.name for g in db.query(Goalie).filter(Goalie.team_id.is_(None)).all()}
    assert names.isdisjoint(forbidden)
