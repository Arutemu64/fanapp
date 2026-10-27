"""rename tickets:generate permission to tickets:manage

The permission now covers the whole tickets tool: listing tickets, issuing them
and choosing which role each TicketsCloud event grants. The permission column is
a VARCHAR guarded by a CHECK constraint (``native_enum=False``), so the rename
is a hand-written constraint swap around an UPDATE of the existing grants: the
constraint is dropped first, since neither the old nor the new one admits both
values at once. Every holder of tickets:generate keeps the access as
tickets:manage.

Revision ID: 9d4f6b2a8e51
Revises: 7c1e5a9b3d20
Create Date: 2026-10-22 13:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "9d4f6b2a8e51"
down_revision = "7c1e5a9b3d20"
branch_labels = None
depends_on = None

_CONSTRAINT = "ck_user_permissions_permissionname"
_TABLE = "user_permissions"
_COLUMN = "permission"

_UNCHANGED = [
    "*",
    "schedule:manage",
    "schedule:import",
    "notifications:send",
    "settings:manage",
    "sync:run",
    "demo:seed",
    "feedback:read",
    "voting:manage",
    "users:read",
    "users:manage",
    "quest:award",
    "quest:manage",
]
_OLD = "tickets:generate"
_NEW = "tickets:manage"


def _rename(old: str, new: str) -> None:
    op.drop_constraint(op.f(_CONSTRAINT), _TABLE, type_="check")
    permissions = sa.table(_TABLE, sa.column(_COLUMN))
    op.execute(
        permissions.update().where(permissions.c[_COLUMN] == old).values({_COLUMN: new})
    )
    op.create_check_constraint(
        op.f(_CONSTRAINT),
        _TABLE,
        sa.column(_COLUMN).in_([*_UNCHANGED, new]),
    )


def upgrade() -> None:
    _rename(_OLD, _NEW)


def downgrade() -> None:
    _rename(_NEW, _OLD)
