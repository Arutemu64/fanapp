"""retire_undeliverable_vote_events

Revision ID: 0fb8aba0836c
Revises: 1957a55f8db9
Create Date: 2026-09-23 08:00:00.000000

"""

from alembic import op

revision = "0fb8aba0836c"
down_revision = "1957a55f8db9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE outbox_events
        SET published_at = now()
        WHERE published_at IS NULL
          AND subject IN ('votes.created', 'votes.deleted')
        """
    )


def downgrade() -> None:
    pass
