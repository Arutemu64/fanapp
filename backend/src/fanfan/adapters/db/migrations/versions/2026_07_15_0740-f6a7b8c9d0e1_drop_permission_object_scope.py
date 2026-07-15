"""drop unused object_id / object_type from user_permissions

The permission scoping columns (object_id / object_type) were speculative
infrastructure: nothing ever populated them with a non-null value and no code
path granted a scoped permission. Drop them along with the NULLS NOT DISTINCT
unique constraint they required, leaving a plain (user_id, permission) uniqueness
rule. A properly-typed scoped-permission model can be reintroduced later if a
real requirement appears.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-15 07:40:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("uq_user_permissions_user_id"), "user_permissions", type_="unique"
    )
    op.drop_column("user_permissions", "object_id")
    op.drop_column("user_permissions", "object_type")
    op.create_unique_constraint(
        op.f("uq_user_permissions_user_id"),
        "user_permissions",
        ["user_id", "permission"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("uq_user_permissions_user_id"), "user_permissions", type_="unique"
    )
    op.add_column(
        "user_permissions",
        sa.Column("object_type", sa.String(), nullable=True),
    )
    op.add_column(
        "user_permissions",
        sa.Column("object_id", sa.Integer(), nullable=True),
    )
    op.create_unique_constraint(
        op.f("uq_user_permissions_user_id"),
        "user_permissions",
        ["user_id", "permission", "object_id", "object_type"],
        postgresql_nulls_not_distinct=True,
    )
