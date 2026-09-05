"""add wildcard permission

Adds the ``*`` value to the ``Permission`` enum — the superuser grant that
satisfies every ``ensure()`` check. The permission column is a VARCHAR guarded
by a CHECK constraint (``native_enum=False``), so a new member is a hand-written
constraint swap — plain Alembic autogenerate does not detect enum member changes.

No grant to the system user: unattended interactors hold the one specific
permission they need (least-privilege, like ``sync:run``); ``*`` is granted to
human organisers by hand via the operator CLI.

Revision ID: a7b8c9d0e1f2
Revises: f1e2d3c4b5a6
Create Date: 2026-09-04 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a7b8c9d0e1f2"
down_revision = "f1e2d3c4b5a6"
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
    "demo:seed",
    "feedback:read",
    "voting:manage",
    "users:read",
]
_NEW = "*"


def upgrade() -> None:
    op.drop_constraint(op.f(_CONSTRAINT), _TABLE, type_="check")
    op.create_check_constraint(
        op.f(_CONSTRAINT),
        _TABLE,
        sa.column(_COLUMN).in_([*_EXISTING, _NEW]),
    )


def downgrade() -> None:
    # Drop any wildcard grants first: the pre-wildcard constraint would reject
    # them, failing the downgrade on a database where "*" was granted.
    permissions = sa.table(_TABLE, sa.column(_COLUMN))
    op.execute(permissions.delete().where(permissions.c[_COLUMN] == _NEW))
    op.drop_constraint(op.f(_CONSTRAINT), _TABLE, type_="check")
    op.create_check_constraint(
        op.f(_CONSTRAINT),
        _TABLE,
        sa.column(_COLUMN).in_(_EXISTING),
    )
