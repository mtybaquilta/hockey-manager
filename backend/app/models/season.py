from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Season(Base):
    __tablename__ = "season"

    id: Mapped[int] = mapped_column(primary_key=True)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    # Plain int (no FK constraint). Validated at the service boundary (set_user_team).
    user_team_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_matchday: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
