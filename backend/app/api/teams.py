from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import TeamNotFound
from app.models import Goalie, Season, Skater, Team, TeamGameplan
from app.schemas.contract import ContractOut
from app.schemas.team import GoalieOut, RosterOut, SkaterOut, TeamOut
from app.services import contract_service
from app.services.generation.players import goalie_overall, skater_overall
from app.services.player_age import age_from_birth_date

router = APIRouter(prefix="/teams", tags=["teams"])


def _team(db: Session, team_id: int) -> Team:
    t = db.query(Team).filter_by(id=team_id).first()
    if not t:
        raise TeamNotFound(f"team {team_id} not found")
    return t


def _current_season_year(db: Session) -> int:
    season = db.query(Season).order_by(Season.id.desc()).first()
    return season.year if season else 0


@router.get("", response_model=list[TeamOut])
def list_teams(db: Session = Depends(get_db)):
    return [
        TeamOut(id=t.id, name=t.name, abbreviation=t.abbreviation)
        for t in db.query(Team).order_by(Team.id).all()
    ]


class TeamSelectPlayer(BaseModel):
    id: int
    name: str
    position: str | None
    ovr: int
    potential: int


class TeamSelectOverview(BaseModel):
    id: int
    name: str
    abbreviation: str
    team_ovr: int
    best_player: TeamSelectPlayer | None
    best_prospect: TeamSelectPlayer | None
    style: str
    line_usage: str
    difficulty: str  # "easy" | "medium" | "hard"


def _difficulty_label(team_ovr: int, league_ovr: float) -> str:
    delta = team_ovr - league_ovr
    if delta >= 1.5:
        return "easy"
    if delta <= -1.5:
        return "hard"
    return "medium"


@router.get("/select-overview", response_model=list[TeamSelectOverview])
def list_team_overviews(db: Session = Depends(get_db)):
    teams = db.query(Team).order_by(Team.id).all()
    skaters_by_team: dict[int, list[Skater]] = {}
    goalies_by_team: dict[int, list[Goalie]] = {}
    for s in db.query(Skater).filter(Skater.team_id.is_not(None)).all():
        skaters_by_team.setdefault(s.team_id, []).append(s)
    for g in db.query(Goalie).filter(Goalie.team_id.is_not(None)).all():
        goalies_by_team.setdefault(g.team_id, []).append(g)
    gameplans = {gp.team_id: gp for gp in db.query(TeamGameplan).all()}

    def _skater_ovr(s: Skater) -> int:
        return skater_overall(s.skating, s.shooting, s.passing, s.defense, s.physical)

    def _goalie_ovr(g: Goalie) -> int:
        return goalie_overall(g.reflexes, g.positioning, g.rebound_control, g.puck_handling, g.mental)

    team_ovrs: dict[int, int] = {}
    for t in teams:
        sks = skaters_by_team.get(t.id, [])
        gks = goalies_by_team.get(t.id, [])
        ovrs = [_skater_ovr(s) for s in sks] + [_goalie_ovr(g) for g in gks]
        team_ovrs[t.id] = round(sum(ovrs) / len(ovrs)) if ovrs else 0

    league_ovr = (sum(team_ovrs.values()) / len(team_ovrs)) if team_ovrs else 0.0

    out: list[TeamSelectOverview] = []
    for t in teams:
        sks = skaters_by_team.get(t.id, [])
        gks = goalies_by_team.get(t.id, [])
        candidates_for_best = [
            (
                _skater_ovr(s),
                TeamSelectPlayer(
                    id=s.id, name=s.name, position=s.position,
                    ovr=_skater_ovr(s), potential=s.potential,
                ),
            )
            for s in sks
        ] + [
            (
                _goalie_ovr(g),
                TeamSelectPlayer(
                    id=g.id, name=g.name, position="G",
                    ovr=_goalie_ovr(g), potential=g.potential,
                ),
            )
            for g in gks
        ]
        best_player = max(candidates_for_best, key=lambda kv: kv[0])[1] if candidates_for_best else None

        # Best prospect = highest potential among players with potential > current ovr.
        prospects = [
            (s.potential - _skater_ovr(s), TeamSelectPlayer(
                id=s.id, name=s.name, position=s.position,
                ovr=_skater_ovr(s), potential=s.potential,
            ))
            for s in sks if s.potential > _skater_ovr(s)
        ] + [
            (g.potential - _goalie_ovr(g), TeamSelectPlayer(
                id=g.id, name=g.name, position="G",
                ovr=_goalie_ovr(g), potential=g.potential,
            ))
            for g in gks if g.potential > _goalie_ovr(g)
        ]
        best_prospect = max(prospects, key=lambda kv: (kv[0], kv[1].potential))[1] if prospects else None

        gp = gameplans.get(t.id)
        out.append(
            TeamSelectOverview(
                id=t.id,
                name=t.name,
                abbreviation=t.abbreviation,
                team_ovr=team_ovrs.get(t.id, 0),
                best_player=best_player,
                best_prospect=best_prospect,
                style=gp.style if gp else "balanced",
                line_usage=gp.line_usage if gp else "balanced",
                difficulty=_difficulty_label(team_ovrs.get(t.id, 0), league_ovr),
            )
        )
    return out


@router.get("/{team_id}", response_model=TeamOut)
def get_team(team_id: int, db: Session = Depends(get_db)):
    t = _team(db, team_id)
    return TeamOut(id=t.id, name=t.name, abbreviation=t.abbreviation)


@router.get("/{team_id}/roster", response_model=RosterOut)
def get_roster(team_id: int, db: Session = Depends(get_db)):
    t = _team(db, team_id)
    year = _current_season_year(db)
    skaters = db.query(Skater).filter_by(team_id=t.id).order_by(Skater.position, Skater.id).all()
    goalies = db.query(Goalie).filter_by(team_id=t.id).order_by(Goalie.id).all()

    skater_out = []
    for s in skaters:
        c = contract_service.get_active_contract_for_skater(db, s.id)
        skater_out.append(
            SkaterOut(
                id=s.id, name=s.name, age=age_from_birth_date(s.birth_date, year),
                position=s.position, potential=s.potential,
                skating=s.skating, shooting=s.shooting, passing=s.passing,
                defense=s.defense, physical=s.physical,
                contract=ContractOut.model_validate(c) if c else None,
            )
        )
    goalie_out = []
    for g in goalies:
        c = contract_service.get_active_contract_for_goalie(db, g.id)
        goalie_out.append(
            GoalieOut(
                id=g.id, name=g.name, age=age_from_birth_date(g.birth_date, year),
                potential=g.potential,
                reflexes=g.reflexes, positioning=g.positioning,
                rebound_control=g.rebound_control, puck_handling=g.puck_handling,
                mental=g.mental,
                contract=ContractOut.model_validate(c) if c else None,
            )
        )
    return RosterOut(
        team=TeamOut(id=t.id, name=t.name, abbreviation=t.abbreviation),
        skaters=skater_out,
        goalies=goalie_out,
    )
