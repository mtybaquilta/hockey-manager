from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Game, PlayoffSeries
from app.schemas.playoffs import (
    PlayoffGameOut,
    PlayoffRoundOut,
    PlayoffSeriesOut,
    PlayoffsOut,
)
from app.services.league_service import get_league

router = APIRouter(prefix="/playoffs", tags=["playoffs"])


@router.get("", response_model=PlayoffsOut)
def get_playoffs(db: Session = Depends(get_db)):
    season = get_league(db)
    series_rows = (
        db.query(PlayoffSeries)
        .filter_by(season_id=season.id)
        .order_by(PlayoffSeries.round, PlayoffSeries.bracket_slot)
        .all()
    )
    series_ids = [s.id for s in series_rows]
    games_by_series: dict[int, list[Game]] = defaultdict(list)
    if series_ids:
        for g in (
            db.query(Game)
            .filter(Game.series_id.in_(series_ids))
            .order_by(Game.game_in_series)
            .all()
        ):
            games_by_series[g.series_id].append(g)

    by_round: dict[int, list[PlayoffSeriesOut]] = defaultdict(list)
    for s in series_rows:
        by_round[s.round].append(
            PlayoffSeriesOut(
                id=s.id,
                round=s.round,
                bracket_slot=s.bracket_slot,
                high_seed=s.high_seed,
                low_seed=s.low_seed,
                high_seed_team_id=s.high_seed_team_id,
                low_seed_team_id=s.low_seed_team_id,
                wins_high=s.wins_high,
                wins_low=s.wins_low,
                winner_team_id=s.winner_team_id,
                status=s.status,
                games=[
                    PlayoffGameOut(
                        id=g.id,
                        matchday=g.matchday,
                        game_in_series=g.game_in_series or 0,
                        home_team_id=g.home_team_id,
                        away_team_id=g.away_team_id,
                        status=g.status,
                        home_score=g.home_score,
                        away_score=g.away_score,
                        result_type=g.result_type,
                    )
                    for g in games_by_series.get(s.id, [])
                ],
            )
        )
    rounds = [
        PlayoffRoundOut(round=r, series=by_round[r]) for r in sorted(by_round)
    ]
    return PlayoffsOut(
        phase=season.phase,
        season_status=season.status,
        champion_team_id=season.champion_team_id,
        rounds=rounds,
    )
