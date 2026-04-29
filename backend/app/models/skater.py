from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Skater(Base):
    __tablename__ = "skater"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[str] = mapped_column(String(2), nullable=False)
    skating: Mapped[int] = mapped_column(Integer, nullable=False)
    shooting: Mapped[int] = mapped_column(Integer, nullable=False)
    passing: Mapped[int] = mapped_column(Integer, nullable=False)
    defense: Mapped[int] = mapped_column(Integer, nullable=False)
    physical: Mapped[int] = mapped_column(Integer, nullable=False)
    potential: Mapped[int] = mapped_column(Integer, nullable=False)
    development_type: Mapped[str] = mapped_column(String(16), nullable=False)
