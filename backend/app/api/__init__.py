from fastapi import APIRouter

from app.api import games, health, league, lineup, schedule, season, standings, teams

api_router = APIRouter(prefix="/api")
for r in (
    health.router,
    league.router,
    teams.router,
    lineup.router,
    schedule.router,
    standings.router,
    games.router,
    season.router,
):
    api_router.include_router(r)
