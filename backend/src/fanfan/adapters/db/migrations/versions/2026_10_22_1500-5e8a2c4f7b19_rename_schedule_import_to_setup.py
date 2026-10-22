"""rename schedule:import permission to schedule:setup

The permission now covers the whole schedule tool: importing the programme and
the schedule settings (the announcement cooldown and the changeover). The
permission column is a VARCHAR guarded by a CHECK constraint
(``native_enum=False``), so the rename is a hand-written constraint swap around
an UPDATE of the existing grants: the constraint is dropped first, since neither
the old nor the new one admits both values at once. Every holder of
schedule:import keeps the access as schedule:setup.

Revision ID: 5e8a2c4f7b19
Revises: 9d4f6b2a8e51
Create Date: 2026-10-22 15:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5e8a2c4f7b19"
down_revision = "9d4f6b2a8e51"
branch_labels = None
depends_on = None

_CONSTRAINT = "ck_user_permissions_permissionname"
_TABLE = "user_permissions"
_COLUMN = "permission"

_UNCHANGED = [
    "*",
    "schedule:manage",
    "notifications:send",
    "settings:manage",
    "tickets:manage",
    "sync:run",
    "demo:seed",
    "feedback:read",
    "voting:manage",
    "users:read",
    "users:manage",
    "quest:award",
    "quest:manage",
]
_OLD = "schedule:import"
_NEW = "schedule:setup"


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
