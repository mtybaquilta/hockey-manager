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
    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        raise TeamNotFound(f"team {team_id} not found")
    data = slots.model_dump()
    skater_ids = [data[k] for k in ALL_SKATER_SLOTS]
    if len(set(skater_ids)) != len(skater_ids):
        raise LineupSlotConflict("a skater appears in multiple slots")
    if data["starting_goalie_id"] == data["backup_goalie_id"]:
        raise LineupSlotConflict("starting and backup goalie must differ")

    skaters = {s.id: s for s in db.query(Skater).filter(Skater.id.in_(skater_ids)).all()}
    if len(skaters) != len(set(skater_ids)):
        raise LineupInvalid("one or more skater ids do not exist")
    for s in skaters.values():
        if s.team_id != team_id:
            raise LineupInvalid(f"skater {s.id} belongs to a different team")
    for pos, slot_names in SKATER_SLOTS_BY_POSITION.items():
        for slot in slot_names:
            sk = skaters[data[slot]]
            if sk.position != pos:
                raise LineupInvalid(f"slot {slot} requires {pos}, got {sk.position}")

    goalies = {
        g.id: g
        for g in db.query(Goalie)
        .filter(Goalie.id.in_([data["starting_goalie_id"], data["backup_goalie_id"]]))
        .all()
    }
    if len(goalies) != 2:
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
