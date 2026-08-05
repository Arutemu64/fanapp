"""add demo:seed permission and grant it to the system user

Adds the ``demo:seed`` value to the ``Permission`` enum. The permission column is
a VARCHAR guarded by a CHECK constraint (``native_enum=False``), so a new member
is a hand-written constraint swap — plain Alembic autogenerate does not detect
enum member changes.

The grant lives in this same migration on purpose. The ``fanfan cli demo seed``
command authenticates as the seeded system user and goes through the same
``perm_service.ensure(...)`` check as an organizer, so **seeding stops working
without this row**. Splitting the grant into its own revision would let it be
dropped in a rebase while the enum member survived. The insert must also follow
the constraint swap, or the CHECK rejects the row.

Revision ID: 3f7a1c9e2b04
Revises: 393ea9d41058
Create Date: 2026-08-05 09:00:00.000000

"""

from uuid import UUID, uuid7

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "3f7a1c9e2b04"
down_revision = "393ea9d41058"
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
    "sync:run",
]
_NEW = "demo:seed"

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
