import random

from sqlalchemy.orm import Session

from app.models import Goalie, Skater
from app.services.generation.names import make_player_name

SKATER_LAYOUT = ["LW"] * 4 + ["C"] * 4 + ["RW"] * 4 + ["LD"] * 3 + ["RD"] * 3
GOALIE_COUNT = 2


def _attr(rng: random.Random) -> int:
    return max(40, min(95, int(rng.gauss(70, 8))))


def _goalie_attr(rng: random.Random) -> int:
    """Goalies skew higher than skaters; otherwise league save% sits well below NHL norms."""
    return max(45, min(95, int(rng.gauss(75, 6))))


def generate_players_for_team(rng: random.Random, db: Session, team_id: int, used_names: set[str]) -> None:
    for pos in SKATER_LAYOUT:
        defense = _attr(rng) if pos in ("LD", "RD") else max(40, _attr(rng) - 5)
        db.add(
            Skater(
                team_id=team_id,
                name=make_player_name(rng, used_names),
                age=rng.randint(19, 35),
                position=pos,
                skating=_attr(rng),
                shooting=_attr(rng),
                passing=_attr(rng),
                defense=defense,
                physical=_attr(rng),
            )
        )
    for _ in range(GOALIE_COUNT):
        db.add(
            Goalie(
                team_id=team_id,
                name=make_player_name(rng, used_names),
                age=rng.randint(20, 36),
                reflexes=_goalie_attr(rng),
                positioning=_goalie_attr(rng),
                rebound_control=_goalie_attr(rng),
                puck_handling=_goalie_attr(rng),
                mental=_goalie_attr(rng),
            )
        )
