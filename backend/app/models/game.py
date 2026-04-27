from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Game(Base):
    __tablename__ = "game"

    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("season.id", ondelete="CASCADE"), index=True)
    matchday: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("team.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("team.id"))
    status: Mapped[str] = mapped_column(String(16), default="scheduled", nullable=False)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_type: Mapped[str | None] = mapped_column(String(3), nullable=True)
    seed: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
