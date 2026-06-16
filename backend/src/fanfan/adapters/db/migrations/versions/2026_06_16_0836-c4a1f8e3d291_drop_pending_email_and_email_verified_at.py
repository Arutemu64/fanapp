"""drop pending_email and email_verified_at

Revision ID: c4a1f8e3d291
Revises: e115fa5e6481
Create Date: 2026-06-16 08:36:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c4a1f8e3d291"
down_revision = "e115fa5e6481"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_users_pending_email", table_name="users")
    op.drop_column("users", "pending_email")
    op.drop_column("users", "email_verified_at")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("pending_email", sa.String(), nullable=True),
    )
    op.create_index("ix_users_pending_email", "users", ["pending_email"], unique=True)
