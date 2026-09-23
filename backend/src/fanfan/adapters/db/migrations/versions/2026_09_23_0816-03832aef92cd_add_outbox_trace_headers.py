"""add_outbox_trace_headers

Revision ID: 03832aef92cd
Revises: 0fb8aba0836c
Create Date: 2026-09-23 08:16:29.206629

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "03832aef92cd"
down_revision = "0fb8aba0836c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable with no default: a catalog-only change on the populated table,
    # and existing rows read as untraced, which is what they are.
    op.add_column(
        "outbox_events",
        sa.Column(
            "trace_headers", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )


def downgrade() -> None:
    op.drop_column("outbox_events", "trace_headers")
