from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SeasonProgression(Base):
    __tablename__ = "season_progression"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_season_id: Mapped[int] = mapped_column(
        ForeignKey("season.id", ondelete="CASCADE"), index=True
    )
    to_season_id: Mapped[int] = mapped_column(
        ForeignKey("season.id", ondelete="CASCADE"), index=True
    )
    player_type: Mapped[str] = mapped_column(String(8), nullable=False)
    player_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    age_before: Mapped[int] = mapped_column(Integer, nullable=False)
    age_after: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_before: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_after: Mapped[int] = mapped_column(Integer, nullable=False)
    potential: Mapped[int] = mapped_column(Integer, nullable=False)
    development_type: Mapped[str] = mapped_column(String(16), nullable=False)
    summary_reason: Mapped[str] = mapped_column(String(16), nullable=False)
