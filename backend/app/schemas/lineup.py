from pydantic import BaseModel


class LineupSlots(BaseModel):
    line1_lw_id: int | None = None
    line1_c_id: int | None = None
    line1_rw_id: int | None = None
    line2_lw_id: int | None = None
    line2_c_id: int | None = None
    line2_rw_id: int | None = None
    line3_lw_id: int | None = None
    line3_c_id: int | None = None
    line3_rw_id: int | None = None
    line4_lw_id: int | None = None
    line4_c_id: int | None = None
    line4_rw_id: int | None = None
    pair1_ld_id: int | None = None
    pair1_rd_id: int | None = None
    pair2_ld_id: int | None = None
    pair2_rd_id: int | None = None
    pair3_ld_id: int | None = None
    pair3_rd_id: int | None = None
    starting_goalie_id: int | None = None
    backup_goalie_id: int | None = None


class LineupOut(LineupSlots):
    team_id: int


class UpdateLineupIn(LineupSlots):
    pass
