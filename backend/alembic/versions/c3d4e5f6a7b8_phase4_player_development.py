"""phase 4: player development & multi-season

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. potential / development_type on skater
    op.add_column("skater", sa.Column("potential", sa.Integer(), nullable=True))
    op.add_column("skater", sa.Column("development_type", sa.String(length=16), nullable=True))
    op.execute(
        """
        UPDATE skater
        SET potential = LEAST(
                100,
                ((skating + shooting + passing + defense + physical) / 5)
                    + CAST(FLOOR(RANDOM() * 7) AS INTEGER)
            ),
            development_type = 'steady'
        """
    )
    op.alter_column("skater", "potential", nullable=False)
    op.alter_column("skater", "development_type", nullable=False)

    # 2. potential / development_type on goalie
    op.add_column("goalie", sa.Column("potential", sa.Integer(), nullable=True))
    op.add_column("goalie", sa.Column("development_type", sa.String(length=16), nullable=True))
    op.execute(
        """
        UPDATE goalie
        SET potential = LEAST(
                100,
                ((reflexes + positioning + rebound_control + puck_handling + mental) / 5)
                    + CAST(FLOOR(RANDOM() * 7) AS INTEGER)
            ),
            development_type = 'steady'
        """
    )
    op.alter_column("goalie", "potential", nullable=False)
    op.alter_column("goalie", "development_type", nullable=False)

    # 3. drop team.season_id (FK + index + column)
    op.drop_index("ix_team_season_id", table_name="team")
    op.drop_constraint("team_season_id_fkey", "team", type_="foreignkey")
    op.drop_column("team", "season_id")

    # 4. create season_progression
    op.create_table(
        "season_progression",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "from_season_id",
            sa.Integer(),
            sa.ForeignKey("season.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "to_season_id",
            sa.Integer(),
            sa.ForeignKey("season.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("player_type", sa.String(length=8), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("age_before", sa.Integer(), nullable=False),
        sa.Column("age_after", sa.Integer(), nullable=False),
        sa.Column("overall_before", sa.Integer(), nullable=False),
        sa.Column("overall_after", sa.Integer(), nullable=False),
        sa.Column("potential", sa.Integer(), nullable=False),
        sa.Column("development_type", sa.String(length=16), nullable=False),
        sa.Column("summary_reason", sa.String(length=16), nullable=False),
    )
    op.create_index(
        "ix_season_progression_from_season_id", "season_progression", ["from_season_id"]
    )
    op.create_index(
        "ix_season_progression_to_season_id", "season_progression", ["to_season_id"]
    )
    op.create_index(
        "ix_season_progression_player_id", "season_progression", ["player_id"]
    )

    # 5. create development_event
    op.create_table(
        "development_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "season_progression_id",
            sa.Integer(),
            sa.ForeignKey("season_progression.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attribute", sa.String(length=32), nullable=False),
        sa.Column("old_value", sa.Integer(), nullable=False),
        sa.Column("new_value", sa.Integer(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=16), nullable=False),
    )
    op.create_index(
        "ix_development_event_season_progression_id",
        "development_event",
        ["season_progression_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_development_event_season_progression_id", table_name="development_event")
    op.drop_table("development_event")
    op.drop_index("ix_season_progression_player_id", table_name="season_progression")
    op.drop_index("ix_season_progression_to_season_id", table_name="season_progression")
    op.drop_index("ix_season_progression_from_season_id", table_name="season_progression")
    op.drop_table("season_progression")
    op.add_column("team", sa.Column("season_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "team_season_id_fkey",
        "team",
        "season",
        ["season_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_team_season_id", "team", ["season_id"])
    op.drop_column("goalie", "development_type")
    op.drop_column("goalie", "potential")
    op.drop_column("skater", "development_type")
    op.drop_column("skater", "potential")
