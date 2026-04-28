from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import GameNotFound
from app.models import Game, GameEvent, Goalie, GoalieGameStat, Skater, SkaterGameStat
from app.schemas.game import EventOut, GameDetailOut, GoalieStatOut, SkaterStatOut

router = APIRouter(prefix="/games", tags=["games"])


@router.get("/{game_id}", response_model=GameDetailOut)
def get_game(game_id: int, db: Session = Depends(get_db)):
    g = db.query(Game).filter_by(id=game_id).first()
    if not g:
        raise GameNotFound(f"game {game_id} not found")
    events = db.query(GameEvent).filter_by(game_id=g.id).order_by(GameEvent.tick, GameEvent.id).all()
    s_stats = db.query(SkaterGameStat).filter_by(game_id=g.id).all()
    g_stats = db.query(GoalieGameStat).filter_by(game_id=g.id).all()
    skater_ids = {s.skater_id for s in s_stats}
    goalie_ids = {s.goalie_id for s in g_stats}
    for e in events:
        for sid in (e.primary_skater_id, e.assist1_id, e.assist2_id):
            if sid is not None:
                skater_ids.add(sid)
        if e.goalie_id is not None:
            goalie_ids.add(e.goalie_id)
    skater_names: dict[int, str] = {
        s.id: s.name for s in db.query(Skater).filter(Skater.id.in_(skater_ids)).all()
    } if skater_ids else {}
    goalie_names: dict[int, str] = {
        g_.id: g_.name for g_ in db.query(Goalie).filter(Goalie.id.in_(goalie_ids)).all()
    } if goalie_ids else {}
    home_goals_p = [0, 0, 0, 0]
    away_goals_p = [0, 0, 0, 0]
    home_shots_p = [0, 0, 0, 0]
    away_shots_p = [0, 0, 0, 0]
    for e in events:
        pidx = max(1, min(4, e.period)) - 1
        is_home = e.team_id == g.home_team_id
        if e.kind in ("save", "goal"):
            (home_shots_p if is_home else away_shots_p)[pidx] += 1
        if e.kind == "goal":
            (home_goals_p if is_home else away_goals_p)[pidx] += 1

    return GameDetailOut(
        id=g.id,
        matchday=g.matchday,
        home_team_id=g.home_team_id,
        away_team_id=g.away_team_id,
        status=g.status,
        home_score=g.home_score,
        away_score=g.away_score,
        home_shots=g.home_shots,
        away_shots=g.away_shots,
        result_type=g.result_type,
        events=[
            EventOut(
                tick=e.tick,
                period=e.period,
                kind=e.kind,
                strength=e.strength,
                team_id=e.team_id,
                primary_skater_id=e.primary_skater_id,
                primary_skater_name=skater_names.get(e.primary_skater_id) if e.primary_skater_id else None,
                assist1_id=e.assist1_id,
                assist1_name=skater_names.get(e.assist1_id) if e.assist1_id else None,
                assist2_id=e.assist2_id,
                assist2_name=skater_names.get(e.assist2_id) if e.assist2_id else None,
                goalie_id=e.goalie_id,
                goalie_name=goalie_names.get(e.goalie_id) if e.goalie_id else None,
                penalty_duration_ticks=e.penalty_duration_ticks,
                shot_quality=e.shot_quality,
            )
            for e in events
        ],
        skater_stats=[
            SkaterStatOut(
                skater_id=s.skater_id,
                skater_name=skater_names.get(s.skater_id, f"#{s.skater_id}"),
                goals=s.goals,
                assists=s.assists,
                shots=s.shots,
            )
            for s in s_stats
        ],
        goalie_stats=[
            GoalieStatOut(
                goalie_id=s.goalie_id,
                goalie_name=goalie_names.get(s.goalie_id, f"#{s.goalie_id}"),
                shots_against=s.shots_against,
                saves=s.saves,
                goals_against=s.goals_against,
            )
            for s in g_stats
        ],
        home_goals_by_period=home_goals_p,
        away_goals_by_period=away_goals_p,
        home_shots_by_period=home_shots_p,
        away_shots_by_period=away_shots_p,
    )
