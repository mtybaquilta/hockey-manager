from pydantic import BaseModel


class LineupSlots(BaseModel):
    line1_lw_id: int
    line1_c_id: int
    line1_rw_id: int
    line2_lw_id: int
    line2_c_id: int
    line2_rw_id: int
    line3_lw_id: int
    line3_c_id: int
    line3_rw_id: int
    line4_lw_id: int
    line4_c_id: int
    line4_rw_id: int
    pair1_ld_id: int
    pair1_rd_id: int
    pair2_ld_id: int
    pair2_rd_id: int
    pair3_ld_id: int
    pair3_rd_id: int
    starting_goalie_id: int
    backup_goalie_id: int


class LineupOut(LineupSlots):
    team_id: int


class UpdateLineupIn(LineupSlots):
    pass
