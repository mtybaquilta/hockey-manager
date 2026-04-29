from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DevelopmentEvent(Base):
    __tablename__ = "development_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    season_progression_id: Mapped[int] = mapped_column(
        ForeignKey("season_progression.id", ondelete="CASCADE"), index=True
    )
    attribute: Mapped[str] = mapped_column(String(32), nullable=False)
    old_value: Mapped[int] = mapped_column(Integer, nullable=False)
    new_value: Mapped[int] = mapped_column(Integer, nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(16), nullable=False)
