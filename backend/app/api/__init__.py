from fastapi import APIRouter

from app.api import games, gameplan, health, league, lineup, players, schedule, season, standings, stats, teams

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
    stats.router,
    players.router,
    gameplan.router,
):
    api_router.include_router(r)
