"""add_outbox_retry_state

Revision ID: 1957a55f8db9
Revises: b88de994c3b1
Create Date: 2026-09-23 07:23:28.141683

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1957a55f8db9"
down_revision = "b88de994c3b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Safe on a populated table in one step: a constant (non-volatile) default
    # is stored in the catalog and returned for existing rows, so NOT NULL holds
    # with no backfill and no table rewrite
    # (https://www.postgresql.org/docs/current/sql-altertable.html). Existing
    # rows read as 0 attempts / due now, which is exactly their current state.
    op.add_column(
        "outbox_events",
        sa.Column(
            "attempts", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
    )
    op.add_column(
        "outbox_events",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("outbox_events", sa.Column("last_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("outbox_events", "last_error")
    op.drop_column("outbox_events", "next_attempt_at")
    op.drop_column("outbox_events", "attempts")
