from collections import defaultdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Game, GameEvent, Goalie, GoalieGameStat, Skater, SkaterGameStat, Standing, Team


class SkaterStatRow(BaseModel):
    skater_id: int
    name: str
    team_id: int
    position: str
    games_played: int
    goals: int
    assists: int
    points: int
    shots: int
    shooting_pct: float


class GoalieStatRow(BaseModel):
    goalie_id: int
    name: str
    team_id: int
    games_played: int
    shots_against: int
    saves: int
    goals_against: int
    save_pct: float
    gaa: float


class TeamStatRow(BaseModel):
    team_id: int
    games_played: int
    wins: int
    losses: int
    ot_losses: int
    points: int
    goals_for: int
    goals_against: int
    diff: int
    goals_per_game: float
    shots_per_game: float
    save_pct: float
    shooting_pct: float
    pp_pct: float
    pk_pct: float


class SkatersOut(BaseModel):
    rows: list[SkaterStatRow]


class GoaliesOut(BaseModel):
    rows: list[GoalieStatRow]


class TeamsOut(BaseModel):
    rows: list[TeamStatRow]


router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/skaters", response_model=SkatersOut)
def get_skater_stats(db: Session = Depends(get_db)):
    rows = (
        db.query(
            SkaterGameStat.skater_id,
            func.count(SkaterGameStat.game_id).label("gp"),
            func.sum(SkaterGameStat.goals).label("g"),
            func.sum(SkaterGameStat.assists).label("a"),
            func.sum(SkaterGameStat.shots).label("s"),
        )
        .group_by(SkaterGameStat.skater_id)
        .all()
    )
    by_id = {r.skater_id: r for r in rows}
    out: list[SkaterStatRow] = []
    for sk in db.query(Skater).all():
        r = by_id.get(sk.id)
        gp = int(r.gp) if r else 0
        g = int(r.g or 0) if r else 0
        a = int(r.a or 0) if r else 0
        s = int(r.s or 0) if r else 0
        out.append(
            SkaterStatRow(
                skater_id=sk.id,
                name=sk.name,
                team_id=sk.team_id,
                position=sk.position,
                games_played=gp,
                goals=g,
                assists=a,
                points=g + a,
                shots=s,
                shooting_pct=(g / s) if s else 0.0,
            )
        )
    out.sort(key=lambda r: (-r.points, -r.goals, r.name))
    return SkatersOut(rows=out)


@router.get("/goalies", response_model=GoaliesOut)
def get_goalie_stats(db: Session = Depends(get_db)):
    rows = (
        db.query(
            GoalieGameStat.goalie_id,
            func.count(GoalieGameStat.game_id).label("gp"),
            func.sum(GoalieGameStat.shots_against).label("sa"),
            func.sum(GoalieGameStat.saves).label("sv"),
            func.sum(GoalieGameStat.goals_against).label("ga"),
        )
        .group_by(GoalieGameStat.goalie_id)
        .all()
    )
    by_id = {r.goalie_id: r for r in rows}
    out: list[GoalieStatRow] = []
    for gk in db.query(Goalie).all():
        r = by_id.get(gk.id)
        gp = int(r.gp) if r else 0
        sa = int(r.sa or 0) if r else 0
        sv = int(r.sv or 0) if r else 0
        ga = int(r.ga or 0) if r else 0
        out.append(
            GoalieStatRow(
                goalie_id=gk.id,
                name=gk.name,
                team_id=gk.team_id,
                games_played=gp,
                shots_against=sa,
                saves=sv,
                goals_against=ga,
                save_pct=(sv / sa) if sa else 0.0,
                gaa=(ga / gp) if gp else 0.0,
            )
        )
    # Goalies with at least 30 SA come first, sorted by SV%; rest by GP.
    out.sort(key=lambda r: (-(r.save_pct if r.shots_against >= 30 else 0.0), -r.games_played, r.name))
    return GoaliesOut(rows=out)


@router.get("/teams", response_model=TeamsOut)
def get_team_stats(db: Session = Depends(get_db)):
    teams = db.query(Team).all()
    standings = {s.team_id: s for s in db.query(Standing).all()}
    games = db.query(Game).filter(Game.status == "simulated").all()

    shots_for = defaultdict(int)
    shots_against_total = defaultdict(int)
    for g in games:
        if g.home_shots is None or g.away_shots is None:
            continue
        shots_for[g.home_team_id] += g.home_shots
        shots_against_total[g.home_team_id] += g.away_shots
        shots_for[g.away_team_id] += g.away_shots
        shots_against_total[g.away_team_id] += g.home_shots

    pp_goals = defaultdict(int)        # team scored on PP
    pp_opportunities = defaultdict(int)  # team had a man advantage (opponent took penalty)
    pk_against = defaultdict(int)       # team allowed a PP goal
    pk_opportunities = defaultdict(int)  # team took a penalty
    game_teams = {g.id: (g.home_team_id, g.away_team_id) for g in games}
    if game_teams:
        events = (
            db.query(GameEvent)
            .filter(GameEvent.game_id.in_(list(game_teams.keys())))
            .all()
        )
    else:
        events = []
    for e in events:
        pair = game_teams.get(e.game_id)
        if not pair:
            continue
        home_id, away_id = pair
        opp_id = away_id if e.team_id == home_id else home_id
        if e.kind == "penalty":
            pk_opportunities[e.team_id] += 1
            pp_opportunities[opp_id] += 1
        elif e.kind == "goal" and e.strength == "PP":
            pp_goals[e.team_id] += 1
            pk_against[opp_id] += 1

    out: list[TeamStatRow] = []
    for t in teams:
        s = standings.get(t.id)
        gp = s.games_played if s else 0
        gf = s.goals_for if s else 0
        ga = s.goals_against if s else 0
        sf = shots_for[t.id]
        sa_total = shots_against_total[t.id]
        ppopp = pp_opportunities[t.id]
        pkopp = pk_opportunities[t.id]
        out.append(
            TeamStatRow(
                team_id=t.id,
                games_played=gp,
                wins=s.wins if s else 0,
                losses=s.losses if s else 0,
                ot_losses=s.ot_losses if s else 0,
                points=s.points if s else 0,
                goals_for=gf,
                goals_against=ga,
                diff=gf - ga,
                goals_per_game=(gf / gp) if gp else 0.0,
                shots_per_game=(sf / gp) if gp else 0.0,
                save_pct=((sa_total - ga) / sa_total) if sa_total else 0.0,
                shooting_pct=(gf / sf) if sf else 0.0,
                pp_pct=(pp_goals[t.id] / ppopp) if ppopp else 0.0,
                pk_pct=(1 - (pk_against[t.id] / pkopp)) if pkopp else 0.0,
            )
        )
    out.sort(key=lambda r: (-r.points, -r.diff))
    return TeamsOut(rows=out)
