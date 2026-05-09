"""phase 8: contracts + birth_date + offseason

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-09 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Season.year (default 2025 for existing rows; non-nullable after backfill)
    op.add_column(
        "season",
        sa.Column("year", sa.Integer(), nullable=False, server_default="2025"),
    )
    # Drop the server_default so future inserts must specify year explicitly.
    op.alter_column("season", "year", server_default=None)


def downgrade() -> None:
    op.drop_column("season", "year")
