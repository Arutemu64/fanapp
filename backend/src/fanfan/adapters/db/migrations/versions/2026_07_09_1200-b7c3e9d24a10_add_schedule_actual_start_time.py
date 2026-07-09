"""add_schedule_actual_start_time

Revision ID: b7c3e9d24a10
Revises: f3a9c1d72b48
Create Date: 2026-07-09 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b7c3e9d24a10"
down_revision = "f3a9c1d72b48"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Real on-stage timestamp; nullable because existing rows have no anchor and
    # never-current events never get one. Timezone-aware: we store/compare UTC.
    op.add_column(
        "schedule",
        sa.Column("actual_start_time", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("schedule", "actual_start_time")
