"""phase 5A: team_gameplan

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "team_gameplan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "team_id",
            sa.Integer(),
            sa.ForeignKey("team.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("style", sa.String(length=16), nullable=False),
        sa.Column("line_usage", sa.String(length=16), nullable=False),
        sa.UniqueConstraint("team_id", name="uq_team_gameplan_team_id"),
        sa.CheckConstraint(
            "style IN ('balanced', 'offensive', 'defensive', 'physical')",
            name="ck_team_gameplan_style",
        ),
        sa.CheckConstraint(
            "line_usage IN ('balanced', 'ride_top_lines', 'roll_all_lines')",
            name="ck_team_gameplan_line_usage",
        ),
    )
    op.create_index("ix_team_gameplan_team_id", "team_gameplan", ["team_id"])
    op.execute(
        """
        INSERT INTO team_gameplan (team_id, style, line_usage)
        SELECT t.id, 'balanced', 'balanced'
        FROM team t
        WHERE NOT EXISTS (
            SELECT 1 FROM team_gameplan tg WHERE tg.team_id = t.id
        )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_team_gameplan_team_id", table_name="team_gameplan")
    op.drop_table("team_gameplan")
