"""add sync:run permission

Adds the ``sync:run`` value to the ``Permission`` enum. The permission column
is a VARCHAR guarded by a CHECK constraint (``native_enum=False``), so a new
member is a hand-written constraint swap — plain Alembic autogenerate does not
detect enum member changes.

Revision ID: b7d2e9f01c34
Revises: ae5c95ce2b28
Create Date: 2026-07-23 10:40:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b7d2e9f01c34"
down_revision = "ae5c95ce2b28"
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
