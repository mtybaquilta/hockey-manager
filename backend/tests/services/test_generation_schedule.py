import random

from app.models import Game, Season
from app.services.generation.schedule import (
    GAMES_PER_PAIRING,
    _round_robin_rounds,
    generate_schedule,
)
from app.services.generation.teams import TEAM_COUNT, generate_teams


def _expected_pairings(n: int) -> int:
    return n * (n - 1) // 2


def test_schedule_total_games_and_matchdays(db):
    s = Season(seed=1)
    db.add(s)
    db.flush()
    teams = generate_teams(random.Random(s.seed), db, s.id)
    generate_schedule(random.Random(s.seed), db, s.id, [t.id for t in teams])
    games = db.query(Game).filter_by(season_id=s.id).all()

    expected_games = _expected_pairings(TEAM_COUNT) * GAMES_PER_PAIRING
    expected_matchdays = (TEAM_COUNT - 1) * GAMES_PER_PAIRING
    assert len(games) == expected_games
    matchdays = sorted({g.matchday for g in games})
    assert matchdays == list(range(1, expected_matchdays + 1))


def test_each_matchday_has_disjoint_teams(db):
    s = Season(seed=1)
    db.add(s)
    db.flush()
    teams = generate_teams(random.Random(s.seed), db, s.id)
    generate_schedule(random.Random(s.seed), db, s.id, [t.id for t in teams])
    games = db.query(Game).filter_by(season_id=s.id).all()
    by_md: dict[int, list[Game]] = {}
    for g in games:
        by_md.setdefault(g.matchday, []).append(g)
    for md, md_games in by_md.items():
        teams_on_md = [g.home_team_id for g in md_games] + [g.away_team_id for g in md_games]
        assert len(teams_on_md) == len(set(teams_on_md)), f"matchday {md} has a team in two games"


def test_each_pair_plays_games_per_pairing_times(db):
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
    assert len(counts) == _expected_pairings(TEAM_COUNT)
    assert all(c == GAMES_PER_PAIRING for c in counts.values())


def test_round_robin_covers_every_pair_exactly_once_for_even_n():
    ids = list(range(1, 9))  # 8 teams
    rounds = _round_robin_rounds(ids)
    assert len(rounds) == len(ids) - 1
    seen: set[tuple[int, int]] = set()
    for rnd in rounds:
        assert len(rnd) == len(ids) // 2
        teams_on_round: list[int] = []
        for h, a in rnd:
            seen.add(tuple(sorted([h, a])))
            teams_on_round.extend([h, a])
        assert len(teams_on_round) == len(set(teams_on_round))
    assert len(seen) == _expected_pairings(len(ids))


def test_round_robin_handles_odd_n_with_byes():
    ids = list(range(1, 8))  # 7 teams -> 6 rounds, one bye per round
    rounds = _round_robin_rounds(ids)
    assert len(rounds) == len(ids)  # n-1 with bye fits at n
    seen: set[tuple[int, int]] = set()
    for rnd in rounds:
        assert len(rnd) == len(ids) // 2  # one team sits out
        for h, a in rnd:
            assert h in ids and a in ids
            seen.add(tuple(sorted([h, a])))
    assert len(seen) == _expected_pairings(len(ids))
