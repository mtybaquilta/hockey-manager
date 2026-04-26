from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class GameEvent(Base):
    __tablename__ = "game_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("game.id", ondelete="CASCADE"), index=True)
    tick: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"))
    primary_skater_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    assist1_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    assist2_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
    goalie_id: Mapped[int | None] = mapped_column(ForeignKey("goalie.id"), nullable=True)
