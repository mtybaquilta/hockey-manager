import random

from sqlalchemy.orm import Session

from app.models import Game

# Target schedule length per team. NHL convention. With 32 teams this fits as
# 2 full round-robins (62) + 20 reused front rounds (20) = 82.
GAMES_PER_TEAM = 82


def _round_robin_rounds(team_ids: list[int]) -> list[list[tuple[int, int]]]:
    """Circle-method round-robin: each round has N/2 disjoint games, and over N-1
    rounds every team plays every other exactly once. Handles even and odd N
    (odd N inserts a bye that is filtered out)."""
    ids = list(team_ids)
    bye: int | None = None
    if len(ids) % 2 == 1:
        bye = -1  # sentinel; never written to the DB
        ids.append(bye)

    n = len(ids)
    fixed, rotating = ids[0], ids[1:]
    rounds: list[list[tuple[int, int]]] = []
    for r in range(n - 1):
        left = [fixed] + rotating[: n // 2 - 1]
        right = list(reversed(rotating[n // 2 - 1:]))
        pairings = [(l, r_) for l, r_ in zip(left, right) if bye not in (l, r_)]
        rounds.append(pairings)
        rotating = [rotating[-1]] + rotating[:-1]
    return rounds


def _schedule_segments(n_teams: int, games_per_team: int) -> list[tuple[int, int]]:
    """Plan how many rounds to play in each repetition. Returns a list of
    (rep_index, rounds_count). Each team plays one game per round, so total
    games_per_team = sum of rounds_count.

    Strategy: play as many full round-robins as fit, then use a partial
    prefix of the rotation for the remainder. For n_teams=32, games_per_team=82:
    full=2 (62 rounds) + partial=20 → 82 rounds total.
    """
    rounds_per_full = n_teams - 1 if n_teams % 2 == 0 else n_teams
    assert games_per_team >= rounds_per_full, (
        f"games_per_team={games_per_team} too small for {n_teams} teams "
        f"(need ≥{rounds_per_full} for one full round-robin)"
    )
    full_reps, partial = divmod(games_per_team, rounds_per_full)
    segments = [(rep, rounds_per_full) for rep in range(full_reps)]
    if partial:
        segments.append((full_reps, partial))
    return segments


def generate_schedule(rng: random.Random, db: Session, season_id: int, team_ids: list[int]) -> None:
    """Round-robin schedule. Each team plays GAMES_PER_TEAM games. Home/away
    alternates per repetition; partial reps reuse the front of the rotation,
    which makes those pairings play one extra time vs the rest."""
    assert len(team_ids) >= 2, "need at least 2 teams"
    rounds = _round_robin_rounds(team_ids)
    segments = _schedule_segments(len(team_ids), GAMES_PER_TEAM)
    matchday = 1
    for rep, take in segments:
        for rnd in rounds[:take]:
            for home, away in rnd:
                h, w = (home, away) if rep % 2 == 0 else (away, home)
                db.add(
                    Game(
                        season_id=season_id,
                        matchday=matchday,
                        home_team_id=h,
                        away_team_id=w,
                        status="scheduled",
                    )
                )
            matchday += 1
    db.flush()
