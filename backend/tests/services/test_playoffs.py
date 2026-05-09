from app.models import Game, PlayoffSeries, Season
from app.services.advance_service import advance_matchday
from app.services.league_service import create_or_reset_league
from app.services.playoff_service import (
    GAMES_TO_WIN,
    R1_PAIRINGS,
    ROUND_FINAL,
    _seeded_team_ids,
)


def _run_to_complete(db) -> None:
    for _ in range(5000):
        res = advance_matchday(db)
        if res["season_phase"] == "offseason":
            return
        if res["season_status"] == "complete":
            return
    raise AssertionError("did not finish season")


def _run_until_playoffs(db) -> None:
    while True:
        season = db.query(Season).order_by(Season.id.desc()).one()
        if season.phase == "playoffs":
            return
        advance_matchday(db)


def test_first_round_bracket_uses_top_16_seeds(db):
    create_or_reset_league(db, seed=11)
    _run_until_playoffs(db)
    season = db.query(Season).order_by(Season.id.desc()).one()
    seeds = _seeded_team_ids(db, season.id)
    assert len(seeds) == 16

    series = (
        db.query(PlayoffSeries)
        .filter_by(season_id=season.id, round=1)
        .order_by(PlayoffSeries.bracket_slot)
        .all()
    )
    assert len(series) == 8
    for slot, s in enumerate(series):
        h, l = R1_PAIRINGS[slot]
        assert s.high_seed == h
        assert s.low_seed == l
        assert s.high_seed_team_id == seeds[h - 1]
        assert s.low_seed_team_id == seeds[l - 1]
        assert s.status == "active"
        assert s.wins_high == 0 and s.wins_low == 0


def test_first_playoff_matchday_schedules_game1_per_series(db):
    create_or_reset_league(db, seed=12)
    _run_until_playoffs(db)
    season = db.query(Season).order_by(Season.id.desc()).one()
    pf_games = (
        db.query(Game)
        .filter_by(season_id=season.id, phase="playoffs", status="scheduled")
        .all()
    )
    assert len(pf_games) == 8
    for g in pf_games:
        assert g.matchday == season.current_matchday
        assert g.game_in_series == 1
        # Game 1 → high seed has home ice
        series = db.query(PlayoffSeries).filter_by(id=g.series_id).one()
        assert g.home_team_id == series.high_seed_team_id


def test_full_playoffs_produces_champion_and_uses_4_rounds(db):
    create_or_reset_league(db, seed=13)
    _run_to_complete(db)
    season = db.query(Season).order_by(Season.id.desc()).one()
    assert season.phase == "offseason"
    assert season.champion_team_id is not None

    rounds = sorted({s.round for s in db.query(PlayoffSeries).all()})
    assert rounds == [1, 2, 3, 4]
    counts = {r: 0 for r in rounds}
    for s in db.query(PlayoffSeries).all():
        counts[s.round] += 1
        assert s.status == "complete"
        assert s.winner_team_id in (s.high_seed_team_id, s.low_seed_team_id)
        assert max(s.wins_high, s.wins_low) == GAMES_TO_WIN
    assert counts == {1: 8, 2: 4, 3: 2, 4: 1}

    final = db.query(PlayoffSeries).filter_by(round=ROUND_FINAL).one()
    assert season.champion_team_id == final.winner_team_id


def test_playoff_games_dont_affect_standings(db):
    create_or_reset_league(db, seed=14)
    _run_until_playoffs(db)
    from app.models import Standing

    season = db.query(Season).order_by(Season.id.desc()).one()
    before = {
        s.team_id: (s.games_played, s.points, s.goals_for, s.goals_against)
        for s in db.query(Standing).filter_by(season_id=season.id).all()
    }
    _run_to_complete(db)
    after = {
        s.team_id: (s.games_played, s.points, s.goals_for, s.goals_against)
        for s in db.query(Standing).filter_by(season_id=season.id).all()
    }
    assert before == after


def test_higher_seed_gets_home_ice_in_games_1257(db):
    create_or_reset_league(db, seed=15)
    _run_to_complete(db)
    season = db.query(Season).order_by(Season.id.desc()).one()
    games = (
        db.query(Game)
        .filter_by(season_id=season.id, phase="playoffs")
        .order_by(Game.matchday, Game.id)
        .all()
    )
    high_home_games = {1, 2, 5, 7}
    for g in games:
        series = db.query(PlayoffSeries).filter_by(id=g.series_id).one()
        if g.game_in_series in high_home_games:
            assert g.home_team_id == series.high_seed_team_id
        else:
            assert g.home_team_id == series.low_seed_team_id
