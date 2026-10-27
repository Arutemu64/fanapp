"""drop_schedule_actual_start_time

Revision ID: 0c1c3b98ba5e
Revises: f3a4b5c6d7e8
Create Date: 2026-08-25 06:08:42.364459

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0c1c3b98ba5e"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("schedule_events", "actual_start_time")


def downgrade() -> None:
    op.add_column(
        "schedule_events",
        sa.Column(
            "actual_start_time",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=True,
        ),
    )
