import random

from sqlalchemy.orm import Session

from app.models import Goalie, Skater
from app.services.generation.names import make_player_name

SKATER_LAYOUT = ["LW"] * 4 + ["C"] * 4 + ["RW"] * 4 + ["LD"] * 3 + ["RD"] * 3
GOALIE_COUNT = 2

DEV_TYPE_WEIGHTS = [
    ("steady", 0.50),
    ("early_bloomer", 0.20),
    ("late_bloomer", 0.20),
    ("boom_or_bust", 0.10),
]


def _attr(rng: random.Random) -> int:
    return max(40, min(95, int(rng.gauss(70, 8))))


def _goalie_attr(rng: random.Random) -> int:
    """Goalies skew higher than skaters; otherwise league save% sits well below NHL norms."""
    return max(45, min(95, int(rng.gauss(75, 6))))


def _pick_dev_type(rng: random.Random) -> str:
    r = rng.random()
    acc = 0.0
    for name, w in DEV_TYPE_WEIGHTS:
        acc += w
        if r < acc:
            return name
    return DEV_TYPE_WEIGHTS[-1][0]


def _potential_for(rng: random.Random, age: int, overall: int) -> int:
    if age <= 22:
        bump = rng.randint(6, 16)
    elif age <= 26:
        bump = rng.randint(2, 8)
    elif age <= 30:
        bump = rng.randint(0, 4)
    else:
        bump = 0
    if rng.random() < 0.05:
        bump = 0
    if age < 25 and rng.random() < 0.05:
        bump += rng.randint(3, 6)
    return max(overall, min(100, overall + bump))


def _skater_overall(skating: int, shooting: int, passing: int, defense: int, physical: int) -> int:
    return round((skating + shooting + passing + defense + physical) / 5)


def _goalie_overall(reflexes: int, positioning: int, rebound_control: int, puck_handling: int, mental: int) -> int:
    return round((reflexes + positioning + rebound_control + puck_handling + mental) / 5)


def generate_players_for_team(rng: random.Random, db: Session, team_id: int, used_names: set[str]) -> None:
    for pos in SKATER_LAYOUT:
        skating = _attr(rng)
        shooting = _attr(rng)
        passing = _attr(rng)
        defense = _attr(rng) if pos in ("LD", "RD") else max(40, _attr(rng) - 5)
        physical = _attr(rng)
        age = rng.randint(19, 35)
        overall = _skater_overall(skating, shooting, passing, defense, physical)
        db.add(
            Skater(
                team_id=team_id,
                name=make_player_name(rng, used_names),
                age=age,
                position=pos,
                skating=skating,
                shooting=shooting,
                passing=passing,
                defense=defense,
                physical=physical,
                potential=_potential_for(rng, age, overall),
                development_type=_pick_dev_type(rng),
            )
        )
    for _ in range(GOALIE_COUNT):
        reflexes = _goalie_attr(rng)
        positioning = _goalie_attr(rng)
        rebound_control = _goalie_attr(rng)
        puck_handling = _goalie_attr(rng)
        mental = _goalie_attr(rng)
        age = rng.randint(20, 36)
        overall = _goalie_overall(reflexes, positioning, rebound_control, puck_handling, mental)
        db.add(
            Goalie(
                team_id=team_id,
                name=make_player_name(rng, used_names),
                age=age,
                reflexes=reflexes,
                positioning=positioning,
                rebound_control=rebound_control,
                puck_handling=puck_handling,
                mental=mental,
                potential=_potential_for(rng, age, overall),
                development_type=_pick_dev_type(rng),
            )
        )
