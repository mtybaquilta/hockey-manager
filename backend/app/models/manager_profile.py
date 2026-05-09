from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ManagerProfile(Base):
    __tablename__ = "manager_profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    current_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("team.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    seasons_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    championships_won: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    career_wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    career_losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    career_ot_losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
