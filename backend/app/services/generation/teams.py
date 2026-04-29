import random

from sqlalchemy.orm import Session

from app.models import Team
from app.services.generation.names import sample_team_names
from app.services.generation.players import generate_players_for_team

TEAM_COUNT = 30


def generate_teams(rng: random.Random, db: Session) -> list[Team]:
    used_names: set[str] = set()
    name_specs = sample_team_names(rng, TEAM_COUNT)
    teams: list[Team] = []
    for spec in name_specs:
        t = Team(name=spec["name"], abbreviation=spec["abbreviation"])
        db.add(t)
        db.flush()
        generate_players_for_team(rng, db, t.id, used_names)
        teams.append(t)
    db.flush()
    return teams
