from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Lineup(Base):
    __tablename__ = "lineup"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id", ondelete="CASCADE"), unique=True)

    line1_lw_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    line1_c_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    line1_rw_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    line2_lw_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    line2_c_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    line2_rw_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    line3_lw_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    line3_c_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    line3_rw_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    line4_lw_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    line4_c_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    line4_rw_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)

    pair1_ld_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    pair1_rd_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    pair2_ld_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    pair2_rd_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    pair3_ld_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    pair3_rd_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)

    starting_goalie_id: Mapped[int | None] = mapped_column(ForeignKey("goalie.id"), nullable=True)
    backup_goalie_id: Mapped[int | None] = mapped_column(ForeignKey("goalie.id"), nullable=True)
