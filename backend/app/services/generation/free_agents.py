import random

from sqlalchemy.orm import Session

from app.models import Goalie, Skater
from app.services.generation.names import make_player_name
from app.services.generation.players import (
    _pick_dev_type,
    _potential_for,
    goalie_overall,
    skater_overall,
)

FA_SKATER_LAYOUT = ["LW"] * 8 + ["C"] * 8 + ["RW"] * 8 + ["LD"] * 8 + ["RD"] * 8
FA_GOALIE_COUNT = 5
FA_SKATER_GEMS = 2
FA_GOALIE_GEMS = 1


def _fa_attr(rng: random.Random) -> int:
    return max(40, min(88, int(rng.gauss(63, 7))))


def _fa_goalie_attr(rng: random.Random) -> int:
    return max(45, min(88, int(rng.gauss(68, 6))))


def _bump(value: int, delta: int) -> int:
    return max(40, min(95, value + delta))


def generate_free_agent_pool(
    rng: random.Random, db: Session, used_names: set[str]
) -> None:
    """Seed the league's initial free-agent pool. Called once during league
    creation, after rostered players. Players have team_id=None.
    """
    skaters: list[Skater] = []
    for pos in FA_SKATER_LAYOUT:
        skating = _fa_attr(rng)
        shooting = _fa_attr(rng)
        passing = _fa_attr(rng)
        defense = _fa_attr(rng) if pos in ("LD", "RD") else max(40, _fa_attr(rng) - 5)
        physical = _fa_attr(rng)
        age = rng.randint(19, 35)
        overall = skater_overall(skating, shooting, passing, defense, physical)
        sk = Skater(
            team_id=None,
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
        db.add(sk)
        skaters.append(sk)

    goalies: list[Goalie] = []
    for _ in range(FA_GOALIE_COUNT):
        reflexes = _fa_goalie_attr(rng)
        positioning = _fa_goalie_attr(rng)
        rebound_control = _fa_goalie_attr(rng)
        puck_handling = _fa_goalie_attr(rng)
        mental = _fa_goalie_attr(rng)
        age = rng.randint(20, 36)
        overall = goalie_overall(
            reflexes, positioning, rebound_control, puck_handling, mental
        )
        g = Goalie(
            team_id=None,
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
        db.add(g)
        goalies.append(g)

    for sk in rng.sample(skaters, FA_SKATER_GEMS):
        delta = rng.randint(8, 14)
        sk.skating = _bump(sk.skating, delta)
        sk.shooting = _bump(sk.shooting, delta)
        sk.passing = _bump(sk.passing, delta)
        sk.defense = _bump(sk.defense, delta)
        sk.physical = _bump(sk.physical, delta)
        sk.potential = _potential_for(
            rng,
            sk.age,
            skater_overall(sk.skating, sk.shooting, sk.passing, sk.defense, sk.physical),
        )

    for g in rng.sample(goalies, FA_GOALIE_GEMS):
        delta = rng.randint(8, 14)
        g.reflexes = _bump(g.reflexes, delta)
        g.positioning = _bump(g.positioning, delta)
        g.rebound_control = _bump(g.rebound_control, delta)
        g.puck_handling = _bump(g.puck_handling, delta)
        g.mental = _bump(g.mental, delta)
        g.potential = _potential_for(
            rng,
            g.age,
            goalie_overall(
                g.reflexes, g.positioning, g.rebound_control, g.puck_handling, g.mental
            ),
        )
