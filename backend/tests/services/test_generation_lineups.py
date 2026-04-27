import random

from app.models import Lineup, Season
from app.services.generation.lineups import generate_default_lineups
from app.services.generation.teams import generate_teams


def test_default_lineup_filled_for_each_team(db):
    s = Season(seed=1)
    db.add(s)
    db.flush()
    teams = generate_teams(random.Random(s.seed), db, s.id)
    generate_default_lineups(db, [t.id for t in teams])
    for t in teams:
        lu = db.query(Lineup).filter_by(team_id=t.id).one()
        for col in lu.__table__.columns:
            if col.name not in ("id", "team_id"):
                assert getattr(lu, col.name) is not None, f"slot {col.name} unset for team {t.id}"
