from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TeamGameplan(Base):
    __tablename__ = "team_gameplan"
    __table_args__ = (
        UniqueConstraint("team_id", name="uq_team_gameplan_team_id"),
        CheckConstraint(
            "style IN ('balanced', 'offensive', 'defensive', 'physical')",
            name="ck_team_gameplan_style",
        ),
        CheckConstraint(
            "line_usage IN ('balanced', 'ride_top_lines', 'roll_all_lines')",
            name="ck_team_gameplan_line_usage",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("team.id", ondelete="CASCADE"), index=True, nullable=False
    )
    style: Mapped[str] = mapped_column(String(16), nullable=False)
    line_usage: Mapped[str] = mapped_column(String(16), nullable=False)
