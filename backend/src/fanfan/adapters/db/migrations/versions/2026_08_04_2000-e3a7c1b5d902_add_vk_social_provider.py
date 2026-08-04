"""add VK to the social_provider CHECK constraint

Alembic does not diff CHECK constraint bodies, so adding a member to a
str_enum_column-backed enum is a hand-written drop + recreate.

Revision ID: e3a7c1b5d902
Revises: d877cbd8955e
Create Date: 2026-08-04 20:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e3a7c1b5d902"
down_revision = "d877cbd8955e"
branch_labels = None
depends_on = None

_TABLE = "social_identities"
_CONSTRAINT = "ck_social_identities_social_provider"
_OLD_PROVIDERS = ["telegram"]
_NEW_PROVIDERS = ["telegram", "vk"]


def upgrade() -> None:
    op.drop_constraint(op.f(_CONSTRAINT), _TABLE, type_="check")
    op.create_check_constraint(
        op.f(_CONSTRAINT),
        _TABLE,
        sa.column("provider").in_(_NEW_PROVIDERS),
    )


def downgrade() -> None:
    op.execute(
        sa.delete(sa.table(_TABLE, sa.column("provider"))).where(
            sa.column("provider") == "vk"
        )
    )
    op.drop_constraint(op.f(_CONSTRAINT), _TABLE, type_="check")
    op.create_check_constraint(
        op.f(_CONSTRAINT),
        _TABLE,
        sa.column("provider").in_(_OLD_PROVIDERS),
    )
