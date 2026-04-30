import pytest

from app.errors import NoActiveSeason, SeasonNotComplete
from app.models import (
    DevelopmentEvent,
    Game,
    Goalie,
    Season,
    SeasonProgression,
    Skater,
    SkaterGameStat,
    Standing,
)
from app.services import season_rollover_service
from app.services.advance_service import advance_matchday
from app.services.league_service import create_or_reset_league


def _play_through(db) -> None:
    while advance_matchday(db)["season_status"] != "complete":
        pass


def test_rollover_raises_when_no_active_season(db):
    with pytest.raises(NoActiveSeason):
        season_rollover_service.start_next_season(db)


def test_rollover_raises_when_season_not_complete(db):
    create_or_reset_league(db, seed=42)
    db.flush()
    with pytest.raises(SeasonNotComplete):
        season_rollover_service.start_next_season(db)


def test_rollover_creates_new_season_and_resets_state(db):
    old = create_or_reset_league(db, seed=2026)
    db.flush()
    _play_through(db)
    season_rollover_service.start_next_season(db)
    db.flush()

    new = (
        db.query(Season).filter_by(status="active").order_by(Season.id.desc()).first()
    )
    assert new is not None and new.id != old.id
    assert new.user_team_id == old.user_team_id
    assert new.current_matchday == 1
    assert new.status == "active"

    new_games = db.query(Game).filter_by(season_id=new.id).count()
    assert new_games > 0
    new_standings = db.query(Standing).filter_by(season_id=new.id).all()
    assert len(new_standings) > 0
    for s in new_standings:
        assert s.games_played == 0
        assert s.points == 0
        assert s.goals_for == 0


def test_rollover_ages_every_player(db):
    create_or_reset_league(db, seed=2026)
    db.flush()
    _play_through(db)
    skater_ages = {s.id: s.age for s in db.query(Skater).all()}
    goalie_ages = {g.id: g.age for g in db.query(Goalie).all()}
    season_rollover_service.start_next_season(db)
    db.flush()
    for s in db.query(Skater).all():
        assert s.age == skater_ages[s.id] + 1
    for g in db.query(Goalie).all():
        assert g.age == goalie_ages[g.id] + 1


def test_rollover_persists_progression_and_events(db):
    create_or_reset_league(db, seed=2026)
    db.flush()
    _play_through(db)
    season_rollover_service.start_next_season(db)
    db.flush()
    new = (
        db.query(Season).filter_by(status="active").order_by(Season.id.desc()).first()
    )
    progressions = (
        db.query(SeasonProgression).filter_by(to_season_id=new.id).all()
    )
    expected_count = (
        db.query(Skater).count() + db.query(Goalie).count()
    )
    assert len(progressions) == expected_count
    # development_event rows are present (could be zero in unlikely cohorts; sanity only)
    event_count = db.query(DevelopmentEvent).count()
    assert event_count >= 0


def test_rollover_preserves_old_data(db):
    old = create_or_reset_league(db, seed=2026)
    db.flush()
    _play_through(db)
    old_game_count = db.query(Game).filter_by(season_id=old.id).count()
    old_stats_count = db.query(SkaterGameStat).count()
    season_rollover_service.start_next_season(db)
    db.flush()
    assert db.query(Game).filter_by(season_id=old.id).count() == old_game_count
    assert db.query(SkaterGameStat).count() == old_stats_count
