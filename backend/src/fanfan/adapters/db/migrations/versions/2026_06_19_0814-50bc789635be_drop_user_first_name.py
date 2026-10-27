"""drop user first_name

Revision ID: 50bc789635be
Revises: a3f7c2d9e4b1
Create Date: 2026-06-19 08:14:59.648601

"""

import sqlalchemy as sa
from alembic import op

revision = "50bc789635be"
down_revision = "a3f7c2d9e4b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("users", "first_name")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("first_name", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
