"""phase 9: manager_profile + drop Season.user_team_id

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-05-09 22:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "manager_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column(
            "current_team_id",
            sa.Integer(),
            sa.ForeignKey("team.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("seasons_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("championships_won", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("career_wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("career_losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("career_ot_losses", sa.Integer(), nullable=False, server_default="0"),
    )
    op.drop_column("season", "user_team_id")


def downgrade() -> None:
    op.add_column(
        "season",
        sa.Column("user_team_id", sa.Integer(), nullable=True),
    )
    op.drop_table("manager_profile")
