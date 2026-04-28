import random

from sqlalchemy.orm import Session

from app.models import Game

GAMES_PER_PAIRING = 3


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


def generate_schedule(rng: random.Random, db: Session, season_id: int, team_ids: list[int]) -> None:
    """Round-robin schedule. Every team plays every other team GAMES_PER_PAIRING
    times. Home/away alternates each repetition for fairness."""
    assert len(team_ids) >= 2, "need at least 2 teams"
    rounds = _round_robin_rounds(team_ids)
    matchday = 1
    for rep in range(GAMES_PER_PAIRING):
        for rnd in rounds:
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
