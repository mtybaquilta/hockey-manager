from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Game, GameEvent, GoalieGameStat, SkaterGameStat
from app.services.advance_service import advance_matchday
from app.services.league_service import get_league


class AdvanceOut(BaseModel):
    advanced_game_ids: list[int]
    current_matchday: int
    season_status: str


class SeasonStatusOut(BaseModel):
    current_matchday: int
    status: str


router = APIRouter(prefix="/season", tags=["season"])


@router.post("/advance", response_model=AdvanceOut)
def post_advance(db: Session = Depends(get_db)):
    res = advance_matchday(db)
    db.commit()
    return AdvanceOut(**res)


@router.get("/status", response_model=SeasonStatusOut)
def get_status(db: Session = Depends(get_db)):
    from app.models import Season

    s = db.query(Season).order_by(Season.id.desc()).first()
    if not s:
        from app.errors import LeagueNotFound

        raise LeagueNotFound("no active league")
    return SeasonStatusOut(current_matchday=s.current_matchday, status=s.status)


class SeasonStatsOut(BaseModel):
    games_played: int
    avg_total_goals_per_game: float
    avg_total_shots_per_game: float
    avg_home_goals: float
    avg_away_goals: float
    avg_home_shots: float
    avg_away_shots: float
    league_save_percentage: float
    league_shooting_percentage: float
    home_win_pct: float
    overtime_pct: float
    shootout_pct: float
    penalties_per_game: float
    pp_goals_per_game: float
    sh_goals_per_game: float
    top_scorer_name: str | None
    top_scorer_points: int
    top_scorer_goals: int
    top_scorer_assists: int
    top_goalie_name: str | None
    top_goalie_save_pct: float
    top_goalie_shots_against: int


@router.get("/stats", response_model=SeasonStatsOut)
def get_stats(db: Session = Depends(get_db)):
    games = db.query(Game).filter(Game.status == "simulated").all()
    n = len(games)
    if n == 0:
        return SeasonStatsOut(
            games_played=0,
            avg_total_goals_per_game=0.0,
            avg_total_shots_per_game=0.0,
            avg_home_goals=0.0,
            avg_away_goals=0.0,
            avg_home_shots=0.0,
            avg_away_shots=0.0,
            league_save_percentage=0.0,
            league_shooting_percentage=0.0,
            home_win_pct=0.0,
            overtime_pct=0.0,
            shootout_pct=0.0,
            penalties_per_game=0.0,
            pp_goals_per_game=0.0,
            sh_goals_per_game=0.0,
            top_scorer_name=None,
            top_scorer_points=0,
            top_scorer_goals=0,
            top_scorer_assists=0,
            top_goalie_name=None,
            top_goalie_save_pct=0.0,
            top_goalie_shots_against=0,
        )
    home_goals = sum(g.home_score or 0 for g in games)
    away_goals = sum(g.away_score or 0 for g in games)
    home_shots = sum(g.home_shots or 0 for g in games)
    away_shots = sum(g.away_shots or 0 for g in games)
    total_goals = home_goals + away_goals
    total_shots = home_shots + away_shots
    home_wins = sum(
        1 for g in games if (g.home_score or 0) > (g.away_score or 0)
    )
    ot_count = sum(1 for g in games if g.result_type == "OT")
    so_count = sum(1 for g in games if g.result_type == "SO")

    game_ids = [g.id for g in games]
    penalty_count = (
        db.query(func.count(GameEvent.id))
        .filter(GameEvent.game_id.in_(game_ids), GameEvent.kind == "penalty")
        .scalar()
        or 0
    )
    pp_goal_count = (
        db.query(func.count(GameEvent.id))
        .filter(GameEvent.game_id.in_(game_ids), GameEvent.kind == "goal", GameEvent.strength == "PP")
        .scalar()
        or 0
    )
    sh_goal_count = (
        db.query(func.count(GameEvent.id))
        .filter(GameEvent.game_id.in_(game_ids), GameEvent.kind == "goal", GameEvent.strength == "SH")
        .scalar()
        or 0
    )

    from app.models import Goalie, Skater  # local import to avoid cycle

    skater_rows = (
        db.query(
            SkaterGameStat.skater_id,
            func.sum(SkaterGameStat.goals).label("g"),
            func.sum(SkaterGameStat.assists).label("a"),
        )
        .group_by(SkaterGameStat.skater_id)
        .all()
    )
    top_skater = max(skater_rows, key=lambda r: ((r.g or 0) + (r.a or 0), r.g or 0), default=None)
    top_scorer_name = None
    top_scorer_g = top_scorer_a = 0
    if top_skater is not None:
        sk = db.query(Skater).filter_by(id=top_skater.skater_id).first()
        top_scorer_name = sk.name if sk else None
        top_scorer_g = top_skater.g or 0
        top_scorer_a = top_skater.a or 0

    goalie_rows = (
        db.query(
            GoalieGameStat.goalie_id,
            func.sum(GoalieGameStat.shots_against).label("sa"),
            func.sum(GoalieGameStat.saves).label("sv"),
        )
        .group_by(GoalieGameStat.goalie_id)
        .all()
    )
    qualified = [r for r in goalie_rows if (r.sa or 0) >= 30]
    pool = qualified or goalie_rows
    top_goalie = max(
        pool,
        key=lambda r: ((r.sv or 0) / r.sa) if r.sa else 0.0,
        default=None,
    )
    top_goalie_name = None
    top_goalie_pct = 0.0
    top_goalie_sa = 0
    if top_goalie is not None and top_goalie.sa:
        gk = db.query(Goalie).filter_by(id=top_goalie.goalie_id).first()
        top_goalie_name = gk.name if gk else None
        top_goalie_pct = (top_goalie.sv or 0) / top_goalie.sa
        top_goalie_sa = top_goalie.sa

    return SeasonStatsOut(
        games_played=n,
        avg_total_goals_per_game=total_goals / n,
        avg_total_shots_per_game=total_shots / n,
        avg_home_goals=home_goals / n,
        avg_away_goals=away_goals / n,
        avg_home_shots=home_shots / n,
        avg_away_shots=away_shots / n,
        league_save_percentage=(total_shots - total_goals) / total_shots if total_shots else 0.0,
        league_shooting_percentage=total_goals / total_shots if total_shots else 0.0,
        home_win_pct=home_wins / n,
        overtime_pct=ot_count / n,
        shootout_pct=so_count / n,
        penalties_per_game=penalty_count / n,
        pp_goals_per_game=pp_goal_count / n,
        sh_goals_per_game=sh_goal_count / n,
        top_scorer_name=top_scorer_name,
        top_scorer_points=top_scorer_g + top_scorer_a,
        top_scorer_goals=top_scorer_g,
        top_scorer_assists=top_scorer_a,
        top_goalie_name=top_goalie_name,
        top_goalie_save_pct=top_goalie_pct,
        top_goalie_shots_against=top_goalie_sa,
    )
