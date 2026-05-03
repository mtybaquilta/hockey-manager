import random

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.errors import LeagueNotFound, TeamNotFound
from app.models import (
    Game,
    GameEvent,
    Goalie,
    GoalieGameStat,
    Lineup,
    Season,
    Skater,
    SkaterGameStat,
    Standing,
    Team,
    TeamGameplan,
)
from app.services.gameplan_service import generate_gameplans_for_league
from app.services.generation.free_agents import generate_free_agent_pool
from app.services.generation.lineups import generate_default_lineups
from app.services.generation.schedule import generate_schedule
from app.services.generation.teams import generate_teams


def _wipe(db: Session) -> None:
    for model in [
        GameEvent,
        SkaterGameStat,
        GoalieGameStat,
        Game,
        Standing,
        Lineup,
        Skater,
        Goalie,
        TeamGameplan,
        Team,
        Season,
    ]:
        db.execute(delete(model))


def create_or_reset_league(db: Session, seed: int | None) -> Season:
    _wipe(db)
    seed_val = seed if seed is not None else random.SystemRandom().randint(1, 2**31 - 1)
    season = Season(seed=seed_val, current_matchday=1, status="active")
    db.add(season)
    db.flush()
    rng = random.Random(seed_val)
    teams = generate_teams(rng, db)
    used_names: set[str] = {p.name for p in db.query(Skater).all()}
    used_names |= {g.name for g in db.query(Goalie).all()}
    generate_free_agent_pool(rng, db, used_names)
    db.flush()
    generate_default_lineups(db, [t.id for t in teams])
    generate_schedule(rng, db, season.id, [t.id for t in teams])
    for t in teams:
        db.add(Standing(team_id=t.id, season_id=season.id))
    season.user_team_id = teams[0].id
    db.flush()
    generate_gameplans_for_league(
        rng, db, [t.id for t in teams], user_team_id=season.user_team_id
    )
    return season


def get_active_season(db: Session) -> Season:
    """Return the season currently being played (status='active'). Used by the
    rollover service when it needs to refuse work on a completed season."""
    season = (
        db.query(Season).filter_by(status="active").order_by(Season.id.desc()).first()
    )
    if not season:
        raise LeagueNotFound("no active league")
    return season


def get_league(db: Session) -> Season:
    """Return the most recent season regardless of status. Used by the league
    API and UI; a completed season is still 'the league' until the user starts
    the next one."""
    season = db.query(Season).order_by(Season.id.desc()).first()
    if not season:
        raise LeagueNotFound("no active league")
    return season


def set_user_team(db: Session, team_id: int) -> Season:
    season = get_league(db)
    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        raise TeamNotFound(f"team {team_id} not in current league")
    season.user_team_id = team.id
    db.flush()
    return season
