"""replace email verification flag with pending email and timestamp

Revision ID: 004
Revises: 003
Create Date: 2026-03-19 20:10:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("pending_email", sa.String(), nullable=True))
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE users
            SET email = lower(email)
            WHERE email IS NOT NULL
              AND email <> lower(email)
            """
        )
    )

    op.create_index(
        op.f("ix_users_pending_email"),
        "users",
        ["pending_email"],
        unique=True,
    )

    op.execute(
        sa.text(
            """
            UPDATE users
            SET email_verified_at = now()
            WHERE is_verified IS TRUE
              AND email IS NOT NULL
            """
        )
    )

    op.drop_column("users", "is_verified")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_verified", sa.Boolean(), server_default="false", nullable=False),
    )

    op.execute(
        sa.text(
            """
            UPDATE users
            SET is_verified = CASE
                WHEN email_verified_at IS NULL THEN false
                ELSE true
            END
            """
        )
    )

    op.drop_index(op.f("ix_users_pending_email"), table_name="users")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "pending_email")
