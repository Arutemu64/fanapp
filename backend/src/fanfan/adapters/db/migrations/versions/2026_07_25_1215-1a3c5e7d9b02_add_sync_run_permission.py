"""add sync:run permission and grant it to the system user

Adds the ``sync:run`` value to the ``Permission`` enum. The permission column is
a VARCHAR guarded by a CHECK constraint (``native_enum=False``), so a new member
is a hand-written constraint swap — plain Alembic autogenerate does not detect
enum member changes.

The grant lives in this same migration on purpose. Cron- and CLI-triggered syncs
authenticate as the seeded system user and go through the same
``perm_service.ensure(...)`` check as an organizer, so **unattended syncing stops
working without this row**. Splitting the grant into its own revision would let
it be dropped in a rebase while the enum member survived, and the failure is
quiet: the run is recorded as a failed SyncRun rather than crashing anything.
The insert must also follow the constraint swap, or the CHECK rejects the row.

Revision ID: 1a3c5e7d9b02
Revises: 0f25d74d8716
Create Date: 2026-07-25 12:15:00.000000

"""

from uuid import UUID, uuid7

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "1a3c5e7d9b02"
down_revision = "0f25d74d8716"
branch_labels = None
depends_on = None

_CONSTRAINT = "ck_user_permissions_permissionname"
_TABLE = "user_permissions"
_COLUMN = "permission"

_EXISTING = [
    "schedule:manage",
    "schedule:import",
    "notifications:send",
    "settings:manage",
    "tickets:generate",
]
_NEW = "sync:run"

# Seeded in b0fbcd2bb975; acts as the current user for CLI/scheduler/NATS work.
SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

user_permissions_table = sa.table(
    _TABLE,
    sa.column("id", sa.Uuid()),
    sa.column("user_id", sa.Uuid()),
    sa.column(_COLUMN, sa.String()),
)


def upgrade() -> None:
    op.drop_constraint(op.f(_CONSTRAINT), _TABLE, type_="check")
    op.create_check_constraint(
        op.f(_CONSTRAINT),
        _TABLE,
        sa.column(_COLUMN).in_([*_EXISTING, _NEW]),
    )
    op.execute(
        postgresql.insert(user_permissions_table)
        .values({"id": uuid7(), "user_id": SYSTEM_USER_ID, _COLUMN: _NEW})
        .on_conflict_do_nothing()
    )


def downgrade() -> None:
    # Drop the grant before restoring the constraint, or the old CHECK would
    # reject the still-present row.
    op.execute(
        sa.delete(user_permissions_table).where(
            user_permissions_table.c.user_id == SYSTEM_USER_ID,
            user_permissions_table.c[_COLUMN] == _NEW,
        )
    )
    op.drop_constraint(op.f(_CONSTRAINT), _TABLE, type_="check")
    op.create_check_constraint(
        op.f(_CONSTRAINT),
        _TABLE,
        sa.column(_COLUMN).in_(_EXISTING),
    )
