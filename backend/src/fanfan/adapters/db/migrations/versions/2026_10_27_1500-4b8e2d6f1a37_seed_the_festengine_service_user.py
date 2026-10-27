"""seed the festengine service user

The FestEngine webhook edits the schedule as this user (docs/adr/0048), so the
history reads "@festengine-bot" and the grant stays off the system user that
cron, the CLI and NATS consumers share. It goes through the same
``perm_service.ensure(...)`` check as an organizer, so the webhook is rejected
without the ``schedule:manage`` row. Revoke it to switch the webhook off.

The hyphen in the username falls outside ``USERNAME_PATTERN``, so no person can
have registered or later take the name. With no password, email or social
identity, nobody can sign in as the user. ``number`` takes a free random value,
like the backfill in a325f3ea2dbc.

Revision ID: 4b8e2d6f1a37
Revises: 7f10b417fdff
Create Date: 2026-10-27 15:00:00.000000

"""

from uuid import UUID, uuid7

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "4b8e2d6f1a37"
down_revision = "7f10b417fdff"
branch_labels = None
depends_on = None

STAGE_CONSOLE_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

users_table = sa.table("users", sa.column("id", sa.Uuid()))
user_permissions_table = sa.table(
    "user_permissions",
    sa.column("id", sa.Uuid()),
    sa.column("user_id", sa.Uuid()),
    sa.column("permission", sa.String()),
)


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO users (
                id, username, hashed_password, avatar_seed, number,
                receive_all_announcements, receive_telegram_notifications,
                receive_vk_notifications, settings, role
            )
            SELECT
                :id, 'festengine-bot', NULL, 'festengine', n,
                false, false, false, '{}'::jsonb, 'organizer'
            FROM generate_series(100000, 999999) AS n
            WHERE NOT EXISTS (SELECT 1 FROM users WHERE users.number = n)
            ORDER BY random()
            LIMIT 1
            ON CONFLICT DO NOTHING
            """
        ).bindparams(id=STAGE_CONSOLE_USER_ID)
    )
    op.execute(
        postgresql.insert(user_permissions_table)
        .values(
            {
                "id": uuid7(),
                "user_id": STAGE_CONSOLE_USER_ID,
                "permission": "schedule:manage",
            }
        )
        .on_conflict_do_nothing()
    )


def downgrade() -> None:
    # Permissions cascade; its schedule changes keep the edit with no author.
    op.execute(sa.delete(users_table).where(users_table.c.id == STAGE_CONSOLE_USER_ID))
