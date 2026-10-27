"""grant schedule:manage to the system user

The FestEngine webhook edits the schedule as the seeded system user and goes
through the same ``perm_service.ensure(...)`` check as an organizer
(docs/adr/0048), so it is rejected without this row. Data only: the enum
already has ``schedule:manage``.

Side effect: any CLI command or NATS consumer acting as the system user may now
edit the schedule too. None does today; only the web routes and the webhook
record schedule changes. Revoke this row to switch the webhook off.

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
