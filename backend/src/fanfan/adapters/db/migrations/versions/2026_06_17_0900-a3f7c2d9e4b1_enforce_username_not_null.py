"""enforce username not null

Every user gets an auto-generated username at registration, so username is a
required identity. Backfill any legacy rows that still have a NULL username
(with a unique, pattern-valid placeholder derived from the id) before adding
the NOT NULL constraint.

Revision ID: a3f7c2d9e4b1
Revises: c4a1f8e3d291
Create Date: 2026-06-17 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "a3f7c2d9e4b1"
down_revision = "c4a1f8e3d291"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE users "
            "SET username = 'user_' || substr(replace(id::text, '-', ''), 1, 12) "
            "WHERE username IS NULL"
        )
    )
    op.alter_column(
        "users",
        "username",
        existing_type=sa.String(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "username",
        existing_type=sa.String(),
        nullable=True,
    )
