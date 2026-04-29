from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import GoalieNotFound, SkaterNotFound
from app.models import Game, Goalie, GoalieGameStat, Skater, SkaterGameStat


class _SkaterAttrs(BaseModel):
    skating: int
    shooting: int
    passing: int
    defense: int
    physical: int


class _GoalieAttrs(BaseModel):
    reflexes: int
    positioning: int
    rebound_control: int
    puck_handling: int
    mental: int


class SkaterTotals(BaseModel):
    games_played: int
    goals: int
    assists: int
    points: int
    shots: int
    shooting_pct: float


class GoalieTotals(BaseModel):
    games_played: int
    shots_against: int
    saves: int
    goals_against: int
    save_pct: float
    gaa: float


class SkaterGameLogRow(BaseModel):
    game_id: int
    matchday: int
    opponent_team_id: int
    is_home: bool
    goals: int
    assists: int
    points: int
    shots: int


class GoalieGameLogRow(BaseModel):
    game_id: int
    matchday: int
    opponent_team_id: int
    is_home: bool
    shots_against: int
    saves: int
    goals_against: int
    save_pct: float


class SkaterDetailOut(BaseModel):
    id: int
    name: str
    age: int
    position: str
    team_id: int
    attributes: _SkaterAttrs
    totals: SkaterTotals
    game_log: list[SkaterGameLogRow]


class GoalieDetailOut(BaseModel):
    id: int
    name: str
    age: int
    team_id: int
    attributes: _GoalieAttrs
    totals: GoalieTotals
    game_log: list[GoalieGameLogRow]


router = APIRouter(prefix="/players", tags=["players"])


@router.get("/skater/{skater_id}", response_model=SkaterDetailOut)
def get_skater(skater_id: int, db: Session = Depends(get_db)):
    sk = db.query(Skater).filter_by(id=skater_id).first()
    if not sk:
        raise SkaterNotFound(f"skater {skater_id} not found")
    rows = (
        db.query(SkaterGameStat, Game)
        .join(Game, SkaterGameStat.game_id == Game.id)
        .filter(SkaterGameStat.skater_id == skater_id)
        .order_by(Game.matchday, Game.id)
        .all()
    )
    log: list[SkaterGameLogRow] = []
    g_total = a_total = s_total = 0
    for stat, gm in rows:
        is_home = gm.home_team_id == sk.team_id
        opp = gm.away_team_id if is_home else gm.home_team_id
        log.append(
            SkaterGameLogRow(
                game_id=gm.id,
                matchday=gm.matchday,
                opponent_team_id=opp,
                is_home=is_home,
                goals=stat.goals,
                assists=stat.assists,
                points=stat.goals + stat.assists,
                shots=stat.shots,
            )
        )
        g_total += stat.goals
        a_total += stat.assists
        s_total += stat.shots
    gp = len(log)
    totals = SkaterTotals(
        games_played=gp,
        goals=g_total,
        assists=a_total,
        points=g_total + a_total,
        shots=s_total,
        shooting_pct=(g_total / s_total) if s_total else 0.0,
    )
    return SkaterDetailOut(
        id=sk.id,
        name=sk.name,
        age=sk.age,
        position=sk.position,
        team_id=sk.team_id,
        attributes=_SkaterAttrs(
            skating=sk.skating,
            shooting=sk.shooting,
            passing=sk.passing,
            defense=sk.defense,
            physical=sk.physical,
        ),
        totals=totals,
        game_log=log,
    )


@router.get("/goalie/{goalie_id}", response_model=GoalieDetailOut)
def get_goalie(goalie_id: int, db: Session = Depends(get_db)):
    gk = db.query(Goalie).filter_by(id=goalie_id).first()
    if not gk:
        raise GoalieNotFound(f"goalie {goalie_id} not found")
    rows = (
        db.query(GoalieGameStat, Game)
        .join(Game, GoalieGameStat.game_id == Game.id)
        .filter(GoalieGameStat.goalie_id == goalie_id)
        .order_by(Game.matchday, Game.id)
        .all()
    )
    log: list[GoalieGameLogRow] = []
    sa_total = sv_total = ga_total = 0
    for stat, gm in rows:
        is_home = gm.home_team_id == gk.team_id
        opp = gm.away_team_id if is_home else gm.home_team_id
        log.append(
            GoalieGameLogRow(
                game_id=gm.id,
                matchday=gm.matchday,
                opponent_team_id=opp,
                is_home=is_home,
                shots_against=stat.shots_against,
                saves=stat.saves,
                goals_against=stat.goals_against,
                save_pct=(stat.saves / stat.shots_against) if stat.shots_against else 0.0,
            )
        )
        sa_total += stat.shots_against
        sv_total += stat.saves
        ga_total += stat.goals_against
    gp = len(log)
    totals = GoalieTotals(
        games_played=gp,
        shots_against=sa_total,
        saves=sv_total,
        goals_against=ga_total,
        save_pct=(sv_total / sa_total) if sa_total else 0.0,
        gaa=(ga_total / gp) if gp else 0.0,
    )
    return GoalieDetailOut(
        id=gk.id,
        name=gk.name,
        age=gk.age,
        team_id=gk.team_id,
        attributes=_GoalieAttrs(
            reflexes=gk.reflexes,
            positioning=gk.positioning,
            rebound_control=gk.rebound_control,
            puck_handling=gk.puck_handling,
            mental=gk.mental,
        ),
        totals=totals,
        game_log=log,
    )
