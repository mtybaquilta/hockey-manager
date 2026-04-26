from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Goalie(Base):
    __tablename__ = "goalie"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    reflexes: Mapped[int] = mapped_column(Integer, nullable=False)
    positioning: Mapped[int] = mapped_column(Integer, nullable=False)
    rebound_control: Mapped[int] = mapped_column(Integer, nullable=False)
    puck_handling: Mapped[int] = mapped_column(Integer, nullable=False)
    mental: Mapped[int] = mapped_column(Integer, nullable=False)
