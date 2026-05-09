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

    # 2. Add birth_date to skater and goalie (nullable initially for backfill).
    op.add_column("skater", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column("goalie", sa.Column("birth_date", sa.Date(), nullable=True))

    # Backfill: birth_date = (season.year - age, deterministic month/day from id).
    # Use the 'season' row with the smallest id as the league-start year anchor.
    bind = op.get_bind()
    league_start_year = bind.execute(
        sa.text("SELECT MIN(year) FROM season")
    ).scalar()
    if league_start_year is None:
        league_start_year = 2025

    # Deterministic month/day from id: mod 12 + 1 for month, mod 28 + 1 for day.
    bind.execute(
        sa.text(
            """
            UPDATE skater
            SET birth_date = make_date(:base_year - age, ((id % 12) + 1)::int, ((id % 28) + 1)::int)
            """
        ),
        {"base_year": league_start_year},
    )
    bind.execute(
        sa.text(
            """
            UPDATE goalie
            SET birth_date = make_date(:base_year - age, ((id % 12) + 1)::int, ((id % 28) + 1)::int)
            """
        ),
        {"base_year": league_start_year},
    )

    op.alter_column("skater", "birth_date", nullable=False)
    op.alter_column("goalie", "birth_date", nullable=False)

    # 3. Drop the age column.
    op.drop_column("skater", "age")
    op.drop_column("goalie", "age")

    # 4. Contract table.
    op.create_table(
        "contract",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("skater_id", sa.Integer(), sa.ForeignKey("skater.id", ondelete="CASCADE"), nullable=True),
        sa.Column("goalie_id", sa.Integer(), sa.ForeignKey("goalie.id", ondelete="CASCADE"), nullable=True),
        sa.Column("length", sa.Integer(), nullable=False),
        sa.Column("signed_season_year", sa.Integer(), nullable=False),
        sa.Column("expires_after_year", sa.Integer(), nullable=False),
        sa.Column("salary", sa.Integer(), nullable=False),
        sa.Column("no_trade_clause", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("terminated_season_year", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(skater_id IS NOT NULL)::int + (goalie_id IS NOT NULL)::int = 1",
            name="contract_player_xor",
        ),
        sa.CheckConstraint(
            "status IN ('active','expired','terminated')",
            name="contract_status_check",
        ),
    )
    op.create_index(
        "ix_contract_skater_id_active",
        "contract",
        ["skater_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND skater_id IS NOT NULL"),
    )
    op.create_index(
        "ix_contract_goalie_id_active",
        "contract",
        ["goalie_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND goalie_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_contract_goalie_id_active", table_name="contract")
    op.drop_index("ix_contract_skater_id_active", table_name="contract")
    op.drop_table("contract")

    op.add_column("skater", sa.Column("age", sa.Integer(), nullable=True))
    op.add_column("goalie", sa.Column("age", sa.Integer(), nullable=True))
    bind = op.get_bind()
    league_start_year = bind.execute(sa.text("SELECT MIN(year) FROM season")).scalar() or 2025
    bind.execute(
        sa.text("UPDATE skater SET age = :y - EXTRACT(YEAR FROM birth_date)::int"),
        {"y": league_start_year},
    )
    bind.execute(
        sa.text("UPDATE goalie SET age = :y - EXTRACT(YEAR FROM birth_date)::int"),
        {"y": league_start_year},
    )
    op.alter_column("skater", "age", nullable=False)
    op.alter_column("goalie", "age", nullable=False)
    op.drop_column("skater", "birth_date")
    op.drop_column("goalie", "birth_date")

    op.drop_column("season", "year")
