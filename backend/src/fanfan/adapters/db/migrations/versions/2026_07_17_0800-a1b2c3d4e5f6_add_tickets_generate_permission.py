"""add tickets:generate permission

Adds the ``tickets:generate`` value to the ``Permission`` enum. The permission
column is a VARCHAR guarded by a CHECK constraint (``native_enum=False``), so a
new member is a hand-written constraint swap — plain Alembic autogenerate does
not detect enum member changes.

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
Create Date: 2026-07-17 08:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "f6a7b8c9d0e1"
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
]
_NEW = "tickets:generate"


def upgrade() -> None:
    op.drop_constraint(op.f(_CONSTRAINT), _TABLE, type_="check")
    op.create_check_constraint(
        op.f(_CONSTRAINT),
        _TABLE,
        sa.column(_COLUMN).in_([*_EXISTING, _NEW]),
    )


def downgrade() -> None:
    op.drop_constraint(op.f(_CONSTRAINT), _TABLE, type_="check")
    op.create_check_constraint(
        op.f(_CONSTRAINT),
        _TABLE,
        sa.column(_COLUMN).in_(_EXISTING),
    )
