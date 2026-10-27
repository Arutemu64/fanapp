"""grant schedule:manage to the system user

The FestEngine webhook (``POST /api/webhooks/festengine``) edits the schedule as
the seeded system user and goes through the same ``perm_service.ensure(...)``
check as an organizer, so it answers 403 without this row (docs/adr/0048).

Data only: ``schedule:manage`` is already an enum member. The grant also lets any
other code running as the system user (cron, CLI, NATS consumers) edit the
schedule. None of them calls a schedule interactor today. To turn the
integration off, unset ``FESTENGINE__WEBHOOK_SECRET`` or revoke this grant.

The downgrade deletes the row whether or not this revision inserted it. No
earlier migration grants the system user ``schedule:manage``; a hand-made grant
would go too.

Revision ID: 680b7d27712f
Revises: 7f10b417fdff
Create Date: 2026-10-27 14:00:00.000000

"""

from uuid import UUID, uuid7

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "680b7d27712f"
down_revision = "7f10b417fdff"
branch_labels = None
depends_on = None

_PERMISSION = "schedule:manage"
SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

user_permissions_table = sa.table(
    "user_permissions",
    sa.column("id", sa.Uuid()),
    sa.column("user_id", sa.Uuid()),
    sa.column("permission", sa.String()),
)


def upgrade() -> None:
    op.execute(
        postgresql.insert(user_permissions_table)
        .values({"id": uuid7(), "user_id": SYSTEM_USER_ID, "permission": _PERMISSION})
        .on_conflict_do_nothing()
    )


def downgrade() -> None:
    op.execute(
        sa.delete(user_permissions_table).where(
            user_permissions_table.c.user_id == SYSTEM_USER_ID,
            user_permissions_table.c.permission == _PERMISSION,
        )
    )
