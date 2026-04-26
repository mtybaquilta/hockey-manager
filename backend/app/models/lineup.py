from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Lineup(Base):
    __tablename__ = "lineup"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id", ondelete="CASCADE"), unique=True)

    line1_lw_id: Mapped[int] = mapped_column(ForeignKey("skater.id"))
    line1_c_id: Mapped[int] = mapped_column(ForeignKey("skater.id"))
    line1_rw_id: Mapped[int] = mapped_column(ForeignKey("skater.id"))
    line2_lw_id: Mapped[int] = mapped_column(ForeignKey("skater.id"))
    line2_c_id: Mapped[int] = mapped_column(ForeignKey("skater.id"))
    line2_rw_id: Mapped[int] = mapped_column(ForeignKey("skater.id"))
    line3_lw_id: Mapped[int] = mapped_column(ForeignKey("skater.id"))
    line3_c_id: Mapped[int] = mapped_column(ForeignKey("skater.id"))
    line3_rw_id: Mapped[int] = mapped_column(ForeignKey("skater.id"))
    line4_lw_id: Mapped[int] = mapped_column(ForeignKey("skater.id"))
    line4_c_id: Mapped[int] = mapped_column(ForeignKey("skater.id"))
    line4_rw_id: Mapped[int] = mapped_column(ForeignKey("skater.id"))

    pair1_ld_id: Mapped[int] = mapped_column(ForeignKey("skater.id"))
    pair1_rd_id: Mapped[int] = mapped_column(ForeignKey("skater.id"))
    pair2_ld_id: Mapped[int] = mapped_column(ForeignKey("skater.id"))
    pair2_rd_id: Mapped[int] = mapped_column(ForeignKey("skater.id"))
    pair3_ld_id: Mapped[int] = mapped_column(ForeignKey("skater.id"))
    pair3_rd_id: Mapped[int] = mapped_column(ForeignKey("skater.id"))

    starting_goalie_id: Mapped[int] = mapped_column(ForeignKey("goalie.id"))
    backup_goalie_id: Mapped[int] = mapped_column(ForeignKey("goalie.id"))
