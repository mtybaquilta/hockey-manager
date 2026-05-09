from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Contract(Base):
    __tablename__ = "contract"
    __table_args__ = (
        CheckConstraint(
            "(skater_id IS NOT NULL)::int + (goalie_id IS NOT NULL)::int = 1",
            name="contract_player_xor",
        ),
        CheckConstraint(
            "status IN ('active','expired','terminated')",
            name="contract_status_check",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    skater_id: Mapped[int | None] = mapped_column(
        ForeignKey("skater.id", ondelete="CASCADE"), nullable=True
    )
    goalie_id: Mapped[int | None] = mapped_column(
        ForeignKey("goalie.id", ondelete="CASCADE"), nullable=True
    )
    length: Mapped[int] = mapped_column(Integer, nullable=False)
    signed_season_year: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_after_year: Mapped[int] = mapped_column(Integer, nullable=False)
    salary: Mapped[int] = mapped_column(Integer, nullable=False)
    no_trade_clause: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    terminated_season_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
