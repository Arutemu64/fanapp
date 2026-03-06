"""add server defaults for uuid ids

Revision ID: 003
Revises: 002
Create Date: 2026-03-06 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

UUID_SERVER_DEFAULT = sa.text("gen_random_uuid()")
UUID_ID_TABLES = (
    "mailings",
    "nominations",
    "notifications",
    "participant_values",
    "participants",
    "push_subs",
    "schedule",
    "schedule_changes",
    "social_accounts",
    "subscriptions",
    "tickets",
    "user_flags",
    "user_permissions",
    "users",
    "votes",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    for table_name in UUID_ID_TABLES:
        op.alter_column(
            table_name,
            "id",
            existing_type=sa.Uuid(),
            existing_nullable=False,
            server_default=UUID_SERVER_DEFAULT,
        )


def downgrade() -> None:
    for table_name in UUID_ID_TABLES:
        op.alter_column(
            table_name,
            "id",
            existing_type=sa.Uuid(),
            existing_nullable=False,
            server_default=None,
        )
