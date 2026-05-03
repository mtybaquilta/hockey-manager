import random

from app.models import Game, Season
from app.services.generation.schedule import (
    GAMES_PER_TEAM,
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
    teams = generate_teams(random.Random(s.seed), db)
    generate_schedule(random.Random(s.seed), db, s.id, [t.id for t in teams])
    games = db.query(Game).filter_by(season_id=s.id).all()

    expected_games = TEAM_COUNT * GAMES_PER_TEAM // 2
    expected_matchdays = GAMES_PER_TEAM
    assert len(games) == expected_games
    matchdays = sorted({g.matchday for g in games})
    assert matchdays == list(range(1, expected_matchdays + 1))


def test_each_matchday_has_disjoint_teams(db):
    s = Season(seed=1)
    db.add(s)
    db.flush()
    teams = generate_teams(random.Random(s.seed), db)
    generate_schedule(random.Random(s.seed), db, s.id, [t.id for t in teams])
    games = db.query(Game).filter_by(season_id=s.id).all()
    by_md: dict[int, list[Game]] = {}
    for g in games:
        by_md.setdefault(g.matchday, []).append(g)
    for md, md_games in by_md.items():
        teams_on_md = [g.home_team_id for g in md_games] + [g.away_team_id for g in md_games]
        assert len(teams_on_md) == len(set(teams_on_md)), f"matchday {md} has a team in two games"


def test_each_team_plays_games_per_team_games(db):
    s = Season(seed=1)
    db.add(s)
    db.flush()
    teams = generate_teams(random.Random(s.seed), db)
    generate_schedule(random.Random(s.seed), db, s.id, [t.id for t in teams])
    games = db.query(Game).filter_by(season_id=s.id).all()

    pair_counts: dict = {}
    team_counts: dict[int, int] = {}
    for g in games:
        key = tuple(sorted([g.home_team_id, g.away_team_id]))
        pair_counts[key] = pair_counts.get(key, 0) + 1
        team_counts[g.home_team_id] = team_counts.get(g.home_team_id, 0) + 1
        team_counts[g.away_team_id] = team_counts.get(g.away_team_id, 0) + 1

    # Every team plays exactly GAMES_PER_TEAM games.
    assert len(team_counts) == TEAM_COUNT
    assert all(c == GAMES_PER_TEAM for c in team_counts.values())
    # Every pair appears at least the floor count of full reps; partial rep
    # adds 1 to a subset. With 32 teams and 82 games: 2 full + 20 prefix → counts ∈ {2, 3}.
    assert len(pair_counts) == _expected_pairings(TEAM_COUNT)
    rounds_per_full = TEAM_COUNT - 1
    full_reps = GAMES_PER_TEAM // rounds_per_full
    assert min(pair_counts.values()) == full_reps
    assert max(pair_counts.values()) <= full_reps + 1


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
