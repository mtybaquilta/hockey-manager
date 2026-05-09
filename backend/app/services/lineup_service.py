from sqlalchemy.orm import Session

from app.errors import LineupInvalid, LineupSlotConflict, TeamNotFound
from app.models import Goalie, Lineup, Skater, Team
from app.schemas.lineup import LineupSlots

SKATER_SLOTS_BY_POSITION: dict[str, list[str]] = {
    "LW": ["line1_lw_id", "line2_lw_id", "line3_lw_id", "line4_lw_id"],
    "C": ["line1_c_id", "line2_c_id", "line3_c_id", "line4_c_id"],
    "RW": ["line1_rw_id", "line2_rw_id", "line3_rw_id", "line4_rw_id"],
    "LD": ["pair1_ld_id", "pair2_ld_id", "pair3_ld_id"],
    "RD": ["pair1_rd_id", "pair2_rd_id", "pair3_rd_id"],
}
ALL_SKATER_SLOTS = [s for v in SKATER_SLOTS_BY_POSITION.values() for s in v]


def update_lineup(db: Session, team_id: int, slots: LineupSlots) -> Lineup:
    """Save a (possibly partial) lineup. Empty slots (None) are allowed; the
    user can fill them later. Validation only runs on slots that have an id.
    """
    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        raise TeamNotFound(f"team {team_id} not found")
    data = slots.model_dump()

    # Skater duplicate check ignores empty slots.
    skater_ids = [data[k] for k in ALL_SKATER_SLOTS]
    non_none_skater_ids = [v for v in skater_ids if v is not None]
    if len(set(non_none_skater_ids)) != len(non_none_skater_ids):
        raise LineupSlotConflict("a skater appears in multiple slots")

    # Goalie duplicate check: only conflict when both slots are filled with the same id.
    sg = data["starting_goalie_id"]
    bg = data["backup_goalie_id"]
    if sg is not None and bg is not None and sg == bg:
        raise LineupSlotConflict("starting and backup goalie must differ")

    if non_none_skater_ids:
        skaters = {
            s.id: s
            for s in db.query(Skater).filter(Skater.id.in_(non_none_skater_ids)).all()
        }
        if len(skaters) != len(set(non_none_skater_ids)):
            raise LineupInvalid("one or more skater ids do not exist")
        for s in skaters.values():
            if s.team_id != team_id:
                raise LineupInvalid(f"skater {s.id} belongs to a different team")
        for pos, slot_names in SKATER_SLOTS_BY_POSITION.items():
            for slot in slot_names:
                sid = data[slot]
                if sid is None:
                    continue
                sk = skaters[sid]
                if sk.position != pos:
                    raise LineupInvalid(
                        f"slot {slot} requires {pos}, got {sk.position}"
                    )

    goalie_ids = [v for v in (sg, bg) if v is not None]
    if goalie_ids:
        goalies = {
            g.id: g
            for g in db.query(Goalie).filter(Goalie.id.in_(goalie_ids)).all()
        }
        if len(goalies) != len(set(goalie_ids)):
            raise LineupInvalid("goalie id does not exist")
        for g in goalies.values():
            if g.team_id != team_id:
                raise LineupInvalid(f"goalie {g.id} belongs to a different team")

    lu = db.query(Lineup).filter_by(team_id=team_id).first()
    if not lu:
        raise TeamNotFound(f"lineup row missing for team {team_id}")
    for k, v in data.items():
        setattr(lu, k, v)
    db.flush()
    return lu
