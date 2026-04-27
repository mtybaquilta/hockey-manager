from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import GameNotFound
from app.models import Game, GameEvent, GoalieGameStat, SkaterGameStat
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
                kind=e.kind,
                team_id=e.team_id,
                primary_skater_id=e.primary_skater_id,
                assist1_id=e.assist1_id,
                assist2_id=e.assist2_id,
                goalie_id=e.goalie_id,
            )
            for e in events
        ],
        skater_stats=[
            SkaterStatOut(skater_id=s.skater_id, goals=s.goals, assists=s.assists, shots=s.shots)
            for s in s_stats
        ],
        goalie_stats=[
            GoalieStatOut(
                goalie_id=s.goalie_id,
                shots_against=s.shots_against,
                saves=s.saves,
                goals_against=s.goals_against,
            )
            for s in g_stats
        ],
    )
