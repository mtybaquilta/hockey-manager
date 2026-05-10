import pytest

from app.errors import NoActiveSeason, OffseasonRequired
from app.models import (
    Contract,
    DevelopmentEvent,
    Game,
    Goalie,
    Season,
    SeasonProgression,
    Skater,
    SkaterGameStat,
    Standing,
)
from app.services import contract_service, season_rollover_service
from app.services.advance_service import advance_matchday
from app.services.league_service import create_or_reset_league
from app.services.player_age import age_from_birth_date


def _play_to_offseason(db) -> None:
    for _ in range(5000):
        res = advance_matchday(db)
        if res["season_phase"] == "offseason":
            return
        if res["season_status"] == "complete":
            return
    raise AssertionError("did not reach offseason")


def test_rollover_raises_when_no_active_season(db):
    db.query(Season).delete()
    db.flush()
    with pytest.raises(NoActiveSeason):
        season_rollover_service.start_next_season(db)


def test_rollover_blocked_outside_offseason(db):
    create_or_reset_league(db, seed=42)
    db.flush()
    with pytest.raises(OffseasonRequired):
        season_rollover_service.start_next_season(db)


def test_rollover_creates_new_season_and_resets_state(db):
    old = create_or_reset_league(db, seed=2026)
    db.flush()
    _play_to_offseason(db)
    season_rollover_service.start_next_season(db)
    db.flush()

    new = (
        db.query(Season).filter_by(status="active").order_by(Season.id.desc()).first()
    )
    assert new is not None and new.id != old.id
    assert new.current_matchday == 1
    assert new.status == "active"
    assert new.phase == "regular_season"
    assert new.year == old.year + 1

    new_games = db.query(Game).filter_by(season_id=new.id).count()
    assert new_games > 0
    new_standings = db.query(Standing).filter_by(season_id=new.id).all()
    assert len(new_standings) > 0
    for s in new_standings:
        assert s.games_played == 0
        assert s.points == 0
        assert s.goals_for == 0


def test_rollover_ages_every_player(db):
    old = create_or_reset_league(db, seed=2026)
    db.flush()
    old_year = old.year
    _play_to_offseason(db)
    skater_ages = {
        s.id: age_from_birth_date(s.birth_date, old_year) for s in db.query(Skater).all()
    }
    goalie_ages = {
        g.id: age_from_birth_date(g.birth_date, old_year) for g in db.query(Goalie).all()
    }
    season_rollover_service.start_next_season(db)
    db.flush()
    new = (
        db.query(Season).filter_by(status="active").order_by(Season.id.desc()).first()
    )
    for s in db.query(Skater).all():
        assert age_from_birth_date(s.birth_date, new.year) == skater_ages[s.id] + 1
    for g in db.query(Goalie).all():
        assert age_from_birth_date(g.birth_date, new.year) == goalie_ages[g.id] + 1


def test_rollover_persists_progression_and_events(db):
    create_or_reset_league(db, seed=2026)
    db.flush()
    _play_to_offseason(db)
    season_rollover_service.start_next_season(db)
    db.flush()
    new = (
        db.query(Season).filter_by(status="active").order_by(Season.id.desc()).first()
    )
    progressions = (
        db.query(SeasonProgression).filter_by(to_season_id=new.id).all()
    )
    expected_count = db.query(Skater).count() + db.query(Goalie).count()
    assert len(progressions) == expected_count
    event_count = db.query(DevelopmentEvent).count()
    assert event_count >= 0


def test_rollover_preserves_old_data(db):
    old = create_or_reset_league(db, seed=2026)
    db.flush()
    _play_to_offseason(db)
    old_game_count = db.query(Game).filter_by(season_id=old.id).count()
    old_stats_count = db.query(SkaterGameStat).count()
    season_rollover_service.start_next_season(db)
    db.flush()
    assert db.query(Game).filter_by(season_id=old.id).count() == old_game_count
    assert db.query(SkaterGameStat).count() == old_stats_count


def test_rollover_expires_contracts_and_frees_players(db_with_league):
    db = db_with_league
    sk = db.query(Skater).filter(Skater.team_id.is_not(None)).first()
    c = contract_service.get_active_contract_for_skater(db, sk.id)
    season = db.query(Season).order_by(Season.id.desc()).one()
    c.expires_after_year = season.year  # expires after this year
    season.phase = "offseason"
    db.flush()

    season_rollover_service.start_next_season(db)
    db.flush()

    db.refresh(c)
    db.refresh(sk)
    assert c.status == "expired"
    assert sk.team_id is None
    # The Contract row remains as history.
    assert db.query(Contract).filter_by(id=c.id).one_or_none() is not None
