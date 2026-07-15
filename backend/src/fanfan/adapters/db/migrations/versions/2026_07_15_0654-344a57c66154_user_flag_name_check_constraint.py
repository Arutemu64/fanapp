"""user_flag_name_check_constraint

Revision ID: 344a57c66154
Revises: c9d4e1f83a27
Create Date: 2026-07-15 06:54:11.093871

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "344a57c66154"
down_revision = "c9d4e1f83a27"
branch_labels = None
depends_on = None

# Allowed UserFlagName values (enum *values*, matching what the domain stores).
# Kept as a literal so the migration is pinned to the schema at this revision
# and does not drift if the enum gains members later.
_FLAG_NAMES = ("voting_contest",)


def upgrade() -> None:
    # Bound the column length to match the ORM Enum(length=64) definition.
    op.alter_column(
        "user_flags",
        "name",
        existing_type=sa.String(),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
    # DB-side guard mirroring the UserFlagName StrEnum (native_enum=False), so
    # raw writes cannot store an unknown flag name.
    op.create_check_constraint(
        op.f("ck_user_flags_userflagname"),
        "user_flags",
        sa.column("name").in_(_FLAG_NAMES),
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_user_flags_userflagname"),
        "user_flags",
        type_="check",
    )
    op.alter_column(
        "user_flags",
        "name",
        existing_type=sa.String(length=64),
        type_=sa.String(),
        existing_nullable=False,
    )
