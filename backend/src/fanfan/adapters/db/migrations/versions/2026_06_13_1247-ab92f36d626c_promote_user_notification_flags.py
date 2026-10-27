"""promote_user_notification_flags

Revision ID: ab92f36d626c
Revises: b0fbcd2bb975
Create Date: 2026-06-13 12:47:06.354403

"""

import sqlalchemy as sa
from alembic import op

revision = "ab92f36d626c"
down_revision = "b0fbcd2bb975"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "receive_all_announcements",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "receive_telegram_notifications",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_users_receive_all_announcements",
        "users",
        ["receive_all_announcements"],
        unique=False,
        postgresql_where=sa.text("receive_all_announcements"),
    )

    op.execute(
        """
        UPDATE users SET
            receive_all_announcements =
                COALESCE((settings->>'receive_all_announcements')::bool, true),
            receive_telegram_notifications =
                COALESCE((settings->>'receive_telegram_notifications')::bool, true)
        """
    )
    op.execute(
        "UPDATE users SET settings = "
        "settings - 'receive_all_announcements' - 'receive_telegram_notifications'"
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE users SET settings = settings
            || jsonb_build_object(
                'receive_all_announcements', receive_all_announcements,
                'receive_telegram_notifications', receive_telegram_notifications
            )
        """
    )
    op.drop_index(
        "ix_users_receive_all_announcements",
        table_name="users",
        postgresql_where=sa.text("receive_all_announcements"),
    )
    op.drop_column("users", "receive_telegram_notifications")
    op.drop_column("users", "receive_all_announcements")
