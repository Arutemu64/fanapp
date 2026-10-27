"""add_quest_awards_user_history_index

Revision ID: f7bfa0725510
Revises: fd9f2839bb05
Create Date: 2026-10-19 03:27:22.449905

"""

import sqlalchemy as sa
from alembic import op

revision = "f7bfa0725510"
down_revision = "fd9f2839bb05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_quest_awards_user_id_created_at",
        "quest_awards",
        ["user_id", sa.literal_column("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_quest_awards_user_id_created_at", table_name="quest_awards")
