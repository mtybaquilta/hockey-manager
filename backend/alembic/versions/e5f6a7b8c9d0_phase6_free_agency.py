"""phase 6: free agency (nullable team_id, nullable lineup FKs)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SKATER_LINEUP_COLS = [
    "line1_lw_id", "line1_c_id", "line1_rw_id",
    "line2_lw_id", "line2_c_id", "line2_rw_id",
    "line3_lw_id", "line3_c_id", "line3_rw_id",
    "line4_lw_id", "line4_c_id", "line4_rw_id",
    "pair1_ld_id", "pair1_rd_id",
    "pair2_ld_id", "pair2_rd_id",
    "pair3_ld_id", "pair3_rd_id",
]
GOALIE_LINEUP_COLS = ["starting_goalie_id", "backup_goalie_id"]


def upgrade() -> None:
    with op.batch_alter_table("skater") as batch:
        batch.alter_column("team_id", nullable=True)
        batch.drop_constraint("skater_team_id_fkey", type_="foreignkey")
        batch.create_foreign_key(
            "skater_team_id_fkey", "team", ["team_id"], ["id"], ondelete="SET NULL"
        )
    with op.batch_alter_table("goalie") as batch:
        batch.alter_column("team_id", nullable=True)
        batch.drop_constraint("goalie_team_id_fkey", type_="foreignkey")
        batch.create_foreign_key(
            "goalie_team_id_fkey", "team", ["team_id"], ["id"], ondelete="SET NULL"
        )
    with op.batch_alter_table("lineup") as batch:
        for col in SKATER_LINEUP_COLS + GOALIE_LINEUP_COLS:
            batch.alter_column(col, nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("lineup") as batch:
        for col in SKATER_LINEUP_COLS + GOALIE_LINEUP_COLS:
            batch.alter_column(col, nullable=False)
    with op.batch_alter_table("goalie") as batch:
        batch.drop_constraint("goalie_team_id_fkey", type_="foreignkey")
        batch.create_foreign_key(
            "goalie_team_id_fkey", "team", ["team_id"], ["id"], ondelete="CASCADE"
        )
        batch.alter_column("team_id", nullable=False)
    with op.batch_alter_table("skater") as batch:
        batch.drop_constraint("skater_team_id_fkey", type_="foreignkey")
        batch.create_foreign_key(
            "skater_team_id_fkey", "team", ["team_id"], ["id"], ondelete="CASCADE"
        )
        batch.alter_column("team_id", nullable=False)
