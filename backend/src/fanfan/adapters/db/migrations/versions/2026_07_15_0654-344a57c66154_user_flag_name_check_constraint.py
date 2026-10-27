"""user_flag_name_check_constraint

Revision ID: 344a57c66154
Revises: c9d4e1f83a27
Create Date: 2026-07-15 06:54:11.093871

"""

import sqlalchemy as sa
from alembic import op

revision = "344a57c66154"
down_revision = "c9d4e1f83a27"
branch_labels = None
depends_on = None

_FLAG_NAMES = ("voting_contest",)


def upgrade() -> None:
    op.alter_column(
        "user_flags",
        "name",
        existing_type=sa.String(),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
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
