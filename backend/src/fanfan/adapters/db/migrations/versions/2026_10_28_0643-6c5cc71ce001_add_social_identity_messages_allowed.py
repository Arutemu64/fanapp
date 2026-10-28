"""add social_identities.messages_allowed

Nullable on purpose: NULL means "never checked", the right value for every
existing row, so there is nothing to backfill.

Revision ID: 6c5cc71ce001
Revises: f9bb80dd4a6f
Create Date: 2026-10-28 06:43:04.576981

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6c5cc71ce001"
down_revision = "f9bb80dd4a6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "social_identities", sa.Column("messages_allowed", sa.Boolean(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("social_identities", "messages_allowed")
