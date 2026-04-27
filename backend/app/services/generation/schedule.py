import random

from sqlalchemy.orm import Session

from app.models import Game

GAMES_PER_PAIRING = 3


def generate_schedule(rng: random.Random, db: Session, season_id: int, team_ids: list[int]) -> None:
    """Round-robin: 4 teams -> 6 unique pairs -> GAMES_PER_PAIRING games each.
    Each matchday has 2 disjoint games. MVP-only: assumes exactly 4 teams."""
    assert len(team_ids) == 4, "MVP schedule generator assumes 4 teams"
    a, b, c, d = team_ids
    rounds = [
        [(a, b), (c, d)],
        [(a, c), (b, d)],
        [(a, d), (b, c)],
    ]
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
