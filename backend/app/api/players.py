from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from sqlalchemy import func

from app.errors import GoalieNotFound, SkaterNotFound
from app.models import (
    DevelopmentEvent,
    Game,
    Goalie,
    GoalieGameStat,
    SeasonProgression,
    Skater,
    SkaterGameStat,
)
from app.schemas.career import (
    GoalieCareerOut,
    GoalieSeasonStatsOut,
    SkaterCareerOut,
    SkaterSeasonStatsOut,
)
from app.schemas.development import DevelopmentEventOut, SeasonProgressionOut


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
    potential: int
    development_type: str
    attributes: _SkaterAttrs
    totals: SkaterTotals
    game_log: list[SkaterGameLogRow]


class GoalieDetailOut(BaseModel):
    id: int
    name: str
    age: int
    team_id: int
    potential: int
    development_type: str
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
        potential=sk.potential,
        development_type=sk.development_type,
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
        potential=gk.potential,
        development_type=gk.development_type,
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


def _build_player_history(
    db: Session, player_type: str, player_id: int, name: str, team_id: int
) -> list[SeasonProgressionOut]:
    rows = (
        db.query(SeasonProgression)
        .filter_by(player_type=player_type, player_id=player_id)
        .order_by(SeasonProgression.to_season_id.desc())
        .all()
    )
    history: list[SeasonProgressionOut] = []
    for sp in rows:
        events = (
            db.query(DevelopmentEvent)
            .filter_by(season_progression_id=sp.id)
            .order_by(DevelopmentEvent.id)
            .all()
        )
        history.append(
            SeasonProgressionOut(
                player_type=sp.player_type,
                player_id=sp.player_id,
                player_name=name,
                team_id=team_id,
                age_before=sp.age_before,
                age_after=sp.age_after,
                overall_before=sp.overall_before,
                overall_after=sp.overall_after,
                potential=sp.potential,
                development_type=sp.development_type,
                summary_reason=sp.summary_reason,
                events=[
                    DevelopmentEventOut(
                        attribute=e.attribute,
                        old_value=e.old_value,
                        new_value=e.new_value,
                        delta=e.delta,
                        reason=e.reason,
                    )
                    for e in events
                ],
            )
        )
    return history


@router.get("/skater/{skater_id}/development")
def get_skater_development(skater_id: int, db: Session = Depends(get_db)):
    sk = db.query(Skater).filter_by(id=skater_id).first()
    if not sk:
        raise SkaterNotFound(f"skater {skater_id} not found")
    history = _build_player_history(db, "skater", sk.id, sk.name, sk.team_id)
    return {
        "player_id": sk.id,
        "name": sk.name,
        "history": [h.model_dump() for h in history],
    }


@router.get("/goalie/{goalie_id}/development")
def get_goalie_development(goalie_id: int, db: Session = Depends(get_db)):
    gk = db.query(Goalie).filter_by(id=goalie_id).first()
    if not gk:
        raise GoalieNotFound(f"goalie {goalie_id} not found")
    history = _build_player_history(db, "goalie", gk.id, gk.name, gk.team_id)
    return {
        "player_id": gk.id,
        "name": gk.name,
        "history": [h.model_dump() for h in history],
    }


@router.get("/skater/{skater_id}/career", response_model=SkaterCareerOut)
def get_skater_career(skater_id: int, db: Session = Depends(get_db)):
    sk = db.query(Skater).filter_by(id=skater_id).first()
    if not sk:
        raise SkaterNotFound(f"skater {skater_id} not found")
    rows = (
        db.query(
            Game.season_id.label("season_id"),
            func.count(SkaterGameStat.id).label("gp"),
            func.coalesce(func.sum(SkaterGameStat.goals), 0).label("g"),
            func.coalesce(func.sum(SkaterGameStat.assists), 0).label("a"),
            func.coalesce(func.sum(SkaterGameStat.shots), 0).label("sog"),
        )
        .join(Game, SkaterGameStat.game_id == Game.id)
        .filter(SkaterGameStat.skater_id == skater_id)
        .group_by(Game.season_id)
        .order_by(Game.season_id)
        .all()
    )
    by_season = [
        SkaterSeasonStatsOut(
            season_id=r.season_id,
            gp=r.gp,
            g=r.g,
            a=r.a,
            pts=r.g + r.a,
            sog=r.sog,
        )
        for r in rows
    ]
    totals = SkaterSeasonStatsOut(
        season_id=0,
        gp=sum(s.gp for s in by_season),
        g=sum(s.g for s in by_season),
        a=sum(s.a for s in by_season),
        pts=sum(s.pts for s in by_season),
        sog=sum(s.sog for s in by_season),
    )
    return SkaterCareerOut(
        player_id=sk.id, name=sk.name, by_season=by_season, totals=totals
    )


@router.get("/goalie/{goalie_id}/career", response_model=GoalieCareerOut)
def get_goalie_career(goalie_id: int, db: Session = Depends(get_db)):
    gk = db.query(Goalie).filter_by(id=goalie_id).first()
    if not gk:
        raise GoalieNotFound(f"goalie {goalie_id} not found")
    rows = (
        db.query(
            Game.season_id.label("season_id"),
            func.count(GoalieGameStat.id).label("gp"),
            func.coalesce(func.sum(GoalieGameStat.shots_against), 0).label("sa"),
            func.coalesce(func.sum(GoalieGameStat.saves), 0).label("sv"),
            func.coalesce(func.sum(GoalieGameStat.goals_against), 0).label("ga"),
        )
        .join(Game, GoalieGameStat.game_id == Game.id)
        .filter(GoalieGameStat.goalie_id == goalie_id)
        .group_by(Game.season_id)
        .order_by(Game.season_id)
        .all()
    )
    by_season = [
        GoalieSeasonStatsOut(
            season_id=r.season_id,
            gp=r.gp,
            shots_against=r.sa,
            saves=r.sv,
            goals_against=r.ga,
            sv_pct=(r.sv / r.sa) if r.sa else 0.0,
        )
        for r in rows
    ]
    total_sa = sum(s.shots_against for s in by_season)
    total_sv = sum(s.saves for s in by_season)
    totals = GoalieSeasonStatsOut(
        season_id=0,
        gp=sum(s.gp for s in by_season),
        shots_against=total_sa,
        saves=total_sv,
        goals_against=sum(s.goals_against for s in by_season),
        sv_pct=(total_sv / total_sa) if total_sa else 0.0,
    )
    return GoalieCareerOut(
        player_id=gk.id, name=gk.name, by_season=by_season, totals=totals
    )
