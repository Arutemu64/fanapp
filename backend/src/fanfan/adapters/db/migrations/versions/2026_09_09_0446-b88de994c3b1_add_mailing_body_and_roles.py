"""add_mailing_body_and_roles

Revision ID: b88de994c3b1
Revises: b8575c07d24a
Create Date: 2026-09-09 04:46:31.158213

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b88de994c3b1"
down_revision = "b8575c07d24a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mailings", sa.Column("body", sa.String(), nullable=True))
    op.add_column(
        "mailings",
        sa.Column("roles", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mailings", "roles")
    op.drop_column("mailings", "body")
