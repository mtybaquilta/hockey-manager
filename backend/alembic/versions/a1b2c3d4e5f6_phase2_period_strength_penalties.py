"""phase 2: period, strength, penalty fields on game_event

Revision ID: a1b2c3d4e5f6
Revises: 9243189bb48c
Create Date: 2026-04-27 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "9243189bb48c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("game_event", sa.Column("period", sa.Integer(), nullable=True))
    op.add_column("game_event", sa.Column("strength", sa.String(length=2), nullable=True))
    op.add_column("game_event", sa.Column("penalty_duration_ticks", sa.Integer(), nullable=True))
    # Backfill period from tick (60 ticks/period, OT = 4)
    op.execute(
        "UPDATE game_event SET period = LEAST(tick / 60 + 1, 4) WHERE period IS NULL"
    )
    op.alter_column("game_event", "period", nullable=False)


def downgrade() -> None:
    op.drop_column("game_event", "penalty_duration_ticks")
    op.drop_column("game_event", "strength")
    op.drop_column("game_event", "period")
