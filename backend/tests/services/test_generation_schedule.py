import random

from app.models import Game, Season
from app.services.generation.schedule import GAMES_PER_PAIRING, generate_schedule
from app.services.generation.teams import generate_teams


def test_schedule_18_games_9_matchdays(db):
    s = Season(seed=1)
    db.add(s)
    db.flush()
    teams = generate_teams(random.Random(s.seed), db, s.id)
    generate_schedule(random.Random(s.seed), db, s.id, [t.id for t in teams])
    games = db.query(Game).filter_by(season_id=s.id).all()
    assert len(games) == 18
    matchdays = sorted({g.matchday for g in games})
    assert matchdays == list(range(1, 10))
    for md in matchdays:
        md_games = [g for g in games if g.matchday == md]
        assert len(md_games) == 2
        teams_on_md = [g.home_team_id for g in md_games] + [g.away_team_id for g in md_games]
        assert len(teams_on_md) == len(set(teams_on_md))


def test_each_pair_plays_three_times(db):
    s = Season(seed=1)
    db.add(s)
    db.flush()
    teams = generate_teams(random.Random(s.seed), db, s.id)
    generate_schedule(random.Random(s.seed), db, s.id, [t.id for t in teams])
    games = db.query(Game).filter_by(season_id=s.id).all()
    counts: dict = {}
    for g in games:
        key = tuple(sorted([g.home_team_id, g.away_team_id]))
        counts[key] = counts.get(key, 0) + 1
    assert all(c == GAMES_PER_PAIRING for c in counts.values())
    assert len(counts) == 6
