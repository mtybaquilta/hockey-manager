import random

from app.models import Goalie, Season, Skater
from app.services.generation.teams import TEAM_COUNT, generate_teams


def test_generates_4_teams_with_full_rosters(db):
    s = Season(seed=1)
    db.add(s)
    db.flush()
    teams = generate_teams(random.Random(s.seed), db, s.id)
    assert len(teams) == TEAM_COUNT
    for t in teams:
        skaters = db.query(Skater).filter_by(team_id=t.id).all()
        goalies = db.query(Goalie).filter_by(team_id=t.id).all()
        assert len(skaters) == 18
        assert len(goalies) == 2
