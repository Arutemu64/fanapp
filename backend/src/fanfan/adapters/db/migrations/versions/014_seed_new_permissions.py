"""seed new permissions

Revision ID: 014
Revises: 013
Create Date: 2026-06-12 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None

# Permission definitions backing the role-based checks that used to be
# hardcoded as `role is UserRole.ORG`. ORG bypasses these via PermissionService,
# but the rows must exist so other roles can be granted them explicitly.
NEW_PERMISSIONS = [
    "schedule:import",
    "notifications:send",
    "settings:manage",
]


def upgrade() -> None:
    permissions_table = sa.table(
        "permissions",
        sa.column("name", sa.String()),
    )
    op.execute(
        postgresql.insert(permissions_table)
        .values([{"name": name} for name in NEW_PERMISSIONS])
        .on_conflict_do_nothing()
    )


def downgrade() -> None:
    permissions_table = sa.table(
        "permissions",
        sa.column("name", sa.String()),
    )
    op.execute(
        sa.delete(permissions_table).where(
            permissions_table.c.name.in_(NEW_PERMISSIONS)
        )
    )
