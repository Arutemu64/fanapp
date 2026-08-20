"""add feedback:read permission

Adds the ``feedback:read`` value to the ``Permission`` enum. The permission
column is a VARCHAR guarded by a CHECK constraint (``native_enum=False``), so a
new member is a hand-written constraint swap — plain Alembic autogenerate does
not detect enum member changes.

No grant to the system user here (unlike ``demo:seed`` / ``sync:run``): reading
feedback is an organiser-only surface reached from the staff toolbox, never from
an unattended CLI/scheduler path, so it is granted per organiser by hand.

Revision ID: c1d2e3f4a5b6
Revises: 3f7a1c9e2b04
Create Date: 2026-08-20 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c1d2e3f4a5b6"
down_revision = "3f7a1c9e2b04"
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
]
_NEW = "feedback:read"


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
