"""phase 7: top-16 playoffs

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-04 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "season",
        sa.Column(
            "phase",
            sa.String(length=16),
            nullable=False,
            server_default="regular_season",
        ),
    )
    op.add_column(
        "season",
        sa.Column("champion_team_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "season_champion_team_fkey",
        "season",
        "team",
        ["champion_team_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "playoff_series",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "season_id",
            sa.Integer(),
            sa.ForeignKey("season.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("bracket_slot", sa.Integer(), nullable=False),
        sa.Column(
            "high_seed_team_id",
            sa.Integer(),
            sa.ForeignKey("team.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "low_seed_team_id",
            sa.Integer(),
            sa.ForeignKey("team.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("high_seed", sa.Integer(), nullable=False),
        sa.Column("low_seed", sa.Integer(), nullable=False),
        sa.Column("wins_high", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins_low", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "winner_team_id",
            sa.Integer(),
            sa.ForeignKey("team.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="active",
        ),
        sa.UniqueConstraint(
            "season_id",
            "round",
            "bracket_slot",
            name="uq_playoff_series_slot",
        ),
    )
    op.create_index("ix_playoff_series_season_id", "playoff_series", ["season_id"])

    op.add_column(
        "game",
        sa.Column(
            "phase",
            sa.String(length=16),
            nullable=False,
            server_default="regular_season",
        ),
    )
    op.add_column(
        "game",
        sa.Column("series_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "game",
        sa.Column("game_in_series", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "game_series_id_fkey",
        "game",
        "playoff_series",
        ["series_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_game_series_id", "game", ["series_id"])


def downgrade() -> None:
    op.drop_index("ix_game_series_id", table_name="game")
    op.drop_constraint("game_series_id_fkey", "game", type_="foreignkey")
    op.drop_column("game", "game_in_series")
    op.drop_column("game", "series_id")
    op.drop_column("game", "phase")

    op.drop_index("ix_playoff_series_season_id", table_name="playoff_series")
    op.drop_table("playoff_series")

    op.drop_constraint("season_champion_team_fkey", "season", type_="foreignkey")
    op.drop_column("season", "champion_team_id")
    op.drop_column("season", "phase")
