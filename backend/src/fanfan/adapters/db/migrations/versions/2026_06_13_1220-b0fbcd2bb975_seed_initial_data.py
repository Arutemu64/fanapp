"""seed initial data

Revision ID: b0fbcd2bb975
Revises: de6f670ed1ba
Create Date: 2026-06-13 12:20:18.805744

"""

from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b0fbcd2bb975"
down_revision = "de6f670ed1ba"
branch_labels = None
depends_on = None

# Singleton row read by SqlAppSettingsGateway.get(), which raises if it is
# missing — so the app cannot start without it. Shape mirrors AppSettings.
DEFAULT_APP_SETTINGS = {
    "voting_enabled": False,
    "limits": {"announcement_timeout": 10},
}

# System user authenticated by RawIdProvider (adapters/auth/providers/raw.py),
# acting as the current user for CLI/scheduler/NATS-consumer interactors. Like
# any other user, it holds no permissions until explicitly granted one — there
# is no role-based bypass (see PermissionService.ensure). If a future
# system-triggered interactor adds a perm_service.ensure(...) check, grant
# this exact user_id the one Permission member it needs via a migration
# (a user_permissions row), least-privilege, same as granting any other user.
# Do not special-case this id or its role in PermissionService.
SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")
SYSTEM_USER_SETTINGS = {
    "items_per_page": 4,
    "receive_all_announcements": False,
    "receive_telegram_notifications": True,
}


def upgrade() -> None:
    app_settings_table = sa.table(
        "app_settings",
        sa.column("id", sa.Integer()),
        sa.column("config", postgresql.JSONB(astext_type=sa.Text())),
    )
    op.execute(
        postgresql.insert(app_settings_table)
        .values({"id": 1, "config": DEFAULT_APP_SETTINGS})
        .on_conflict_do_nothing()
    )

    users_table = sa.table(
        "users",
        sa.column("id", sa.Uuid()),
        sa.column("username", sa.String()),
        sa.column("hashed_password", sa.String()),
        sa.column("email", sa.String()),
        sa.column("pending_email", sa.String()),
        sa.column("email_verified_at", sa.DateTime(timezone=True)),
        sa.column("settings", postgresql.JSONB(astext_type=sa.Text())),
        sa.column("first_name", sa.String()),
        sa.column("role", sa.String()),
    )
    op.execute(
        postgresql.insert(users_table)
        .values(
            {
                "id": SYSTEM_USER_ID,
                "username": "system",
                "hashed_password": None,
                "email": None,
                "pending_email": None,
                "email_verified_at": None,
                "settings": SYSTEM_USER_SETTINGS,
                "first_name": None,
                "role": "ORG",
            }
        )
        .on_conflict_do_nothing()
    )


def downgrade() -> None:
    users_table = sa.table(
        "users",
        sa.column("id", sa.Uuid()),
        sa.column("username", sa.String()),
    )
    op.execute(
        sa.delete(users_table).where(
            users_table.c.id == SYSTEM_USER_ID,
            users_table.c.username == "system",
        )
    )

    app_settings_table = sa.table(
        "app_settings",
        sa.column("id", sa.Integer()),
    )
    op.execute(sa.delete(app_settings_table).where(app_settings_table.c.id == 1))
