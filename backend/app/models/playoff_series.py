from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PlayoffSeries(Base):
    __tablename__ = "playoff_series"
    __table_args__ = (
        UniqueConstraint(
            "season_id", "round", "bracket_slot", name="uq_playoff_series_slot"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("season.id", ondelete="CASCADE"), index=True
    )
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    bracket_slot: Mapped[int] = mapped_column(Integer, nullable=False)
    high_seed_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("team.id", ondelete="SET NULL"), nullable=True
    )
    low_seed_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("team.id", ondelete="SET NULL"), nullable=True
    )
    high_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    low_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    wins_high: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wins_low: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    winner_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("team.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
