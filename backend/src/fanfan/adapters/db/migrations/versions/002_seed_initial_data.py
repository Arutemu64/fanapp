"""seed initial data

Revision ID: 002
Revises: 001
Create Date: 2026-03-04 21:35:00.000000

"""

from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")
SYSTEM_USER_SETTINGS = {"items_per_page": 4, "receive_all_announcements": False}
DEFAULT_APP_SETTINGS = {
    "voting_enabled": False,
    "limits": {"announcement_timeout": 10},
}
PERMISSIONS = [
    "schedule:manage",
]
USER_ROLE_ENUM = postgresql.ENUM(
    "VISITOR",
    "PARTICIPANT",
    "HELPER",
    "ORG",
    name="userrole",
    create_type=False,
)


def upgrade() -> None:
    permissions_table = sa.table(
        "permissions",
        sa.column("name", sa.String()),
    )
    op.execute(
        postgresql.insert(permissions_table)
        .values([{"name": name} for name in PERMISSIONS])
        .on_conflict_do_nothing()
    )

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
        sa.column("is_verified", sa.Boolean()),
        sa.column("settings", postgresql.JSONB(astext_type=sa.Text())),
        sa.column("first_name", sa.String()),
        sa.column("role", USER_ROLE_ENUM),
    )
    op.execute(
        postgresql.insert(users_table)
        .values(
            {
                "id": SYSTEM_USER_ID,
                "username": "system",
                "hashed_password": None,
                "email": None,
                "is_verified": False,
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
        sa.column("config", postgresql.JSONB(astext_type=sa.Text())),
    )
    op.execute(
        sa.delete(app_settings_table).where(
            app_settings_table.c.id == 1,
            app_settings_table.c.config == DEFAULT_APP_SETTINGS,
        )
    )

    permissions_table = sa.table(
        "permissions",
        sa.column("name", sa.String()),
    )
    op.execute(
        sa.delete(permissions_table).where(permissions_table.c.name.in_(PERMISSIONS))
    )
