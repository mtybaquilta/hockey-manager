from app.models import Contract, Season, Skater
from app.services.advance_service import advance_matchday
from app.services.league_service import create_or_reset_league
from app.services.season_rollover_service import start_next_season


def test_full_loop_through_rollover(db):
    create_or_reset_league(db, seed=99)
    db.flush()
    s0 = db.query(Season).order_by(Season.id.desc()).one()
    initial_contracts = db.query(Contract).filter_by(status="active").count()
    assert initial_contracts > 0

    for _ in range(5000):
        res = advance_matchday(db)
        if res["season_phase"] == "offseason":
            break
        if res["season_status"] == "complete":
            raise AssertionError("season ended without entering offseason")
    else:
        raise AssertionError("did not reach offseason")

    start_next_season(db)
    db.flush()

    s1 = db.query(Season).filter_by(status="active").one()
    assert s1.year == s0.year + 1
    assert s1.phase == "regular_season"

    res = advance_matchday(db)
    assert res["season_phase"] == "regular_season"

    expired = db.query(Contract).filter_by(status="expired").count()
    assert expired >= 1

    # Players whose contracts expired and weren't on a roster anymore.
    freed_skaters = (
        db.query(Skater)
        .filter(Skater.team_id.is_(None))
        .count()
    )
    assert freed_skaters >= 0  # smoke
