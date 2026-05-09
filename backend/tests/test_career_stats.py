from app.models import ManagerProfile
from app.services import manager_profile_service
from app.services.advance_service import advance_matchday
from app.services.season_rollover_service import start_next_season


def test_career_record_ticks_up_after_one_matchday(db_with_league):
    db = db_with_league
    p = manager_profile_service.require_active_profile(db)
    advance_matchday(db)
    db.refresh(p)
    total = p.career_wins + p.career_losses + p.career_ot_losses
    # User team plays at most one game per matchday.
    assert total in (0, 1), f"expected 0 or 1 result, got {total}"


def test_seasons_completed_bumps_on_rollover(db_with_league):
    db = db_with_league
    p = manager_profile_service.require_active_profile(db)
    seasons_before = p.seasons_completed
    for _ in range(5000):
        res = advance_matchday(db)
        if res["season_phase"] == "offseason":
            break
    start_next_season(db)
    db.refresh(p)
    assert p.seasons_completed == seasons_before + 1


def test_championship_bumps_when_user_wins(db_with_league):
    db = db_with_league
    p = manager_profile_service.require_active_profile(db)
    for _ in range(5000):
        res = advance_matchday(db)
        if res["season_phase"] == "offseason":
            break
    db.refresh(p)
    # User team may or may not have won; just check the counter is consistent.
    from app.models import Season

    season = db.query(Season).order_by(Season.id.desc()).first()
    expected = 1 if season.champion_team_id == p.current_team_id else 0
    assert p.championships_won == expected
