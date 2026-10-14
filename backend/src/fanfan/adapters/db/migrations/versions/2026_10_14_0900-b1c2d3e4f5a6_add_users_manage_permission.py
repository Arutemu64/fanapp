"""add users:manage permission

Adds the ``users:manage`` value to the ``Permission`` enum: changing another
user's role from the organiser user directory. The permission column is a
VARCHAR guarded by a CHECK constraint (``native_enum=False``), so a new member
is a hand-written constraint swap — plain Alembic autogenerate does not detect
enum member changes.

Widening the allowed set touches no existing row, so there is nothing to
backfill.

Revision ID: b1c2d3e4f5a6
Revises: 03832aef92cd
Create Date: 2026-10-14 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b1c2d3e4f5a6"
down_revision = "03832aef92cd"
branch_labels = None
depends_on = None

_CONSTRAINT = "ck_user_permissions_permissionname"
_TABLE = "user_permissions"
_COLUMN = "permission"

_EXISTING = [
    "*",
    "schedule:manage",
    "schedule:import",
    "notifications:send",
    "settings:manage",
    "tickets:generate",
    "sync:run",
    "demo:seed",
    "feedback:read",
    "voting:manage",
    "users:read",
]
_NEW = "users:manage"


def upgrade() -> None:
    op.drop_constraint(op.f(_CONSTRAINT), _TABLE, type_="check")
    op.create_check_constraint(
        op.f(_CONSTRAINT),
        _TABLE,
        sa.column(_COLUMN).in_([*_EXISTING, _NEW]),
    )


def downgrade() -> None:
    # Drop any users:manage grants first: the narrower constraint would reject
    # them, failing the downgrade on a database where it was granted.
    permissions = sa.table(_TABLE, sa.column(_COLUMN))
    op.execute(permissions.delete().where(permissions.c[_COLUMN] == _NEW))
    op.drop_constraint(op.f(_CONSTRAINT), _TABLE, type_="check")
    op.create_check_constraint(
        op.f(_CONSTRAINT),
        _TABLE,
        sa.column(_COLUMN).in_(_EXISTING),
    )
