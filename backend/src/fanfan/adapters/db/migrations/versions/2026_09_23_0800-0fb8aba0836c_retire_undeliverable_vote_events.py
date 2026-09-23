"""retire_undeliverable_vote_events

Revision ID: 0fb8aba0836c
Revises: 1957a55f8db9
Create Date: 2026-09-23 08:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0fb8aba0836c"
down_revision = "1957a55f8db9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # VoteCreated/VoteDeleted were written to the outbox but no subscriber ever
    # consumed them, so their subjects were never part of the JetStream stream
    # and every relay publish failed ("no response from stream"). The events are
    # gone from the code; mark any rows still queued as published so the relay
    # stops retrying them. Marked rather than deleted: the retention purge drops
    # them like any delivered row, and until then they stay inspectable.
    op.execute(
        """
        UPDATE outbox_events
        SET published_at = now()
        WHERE published_at IS NULL
          AND subject IN ('votes.created', 'votes.deleted')
        """
    )


def downgrade() -> None:
    # Irreversible by design: re-queueing the rows would only restore events
    # that can never be delivered.
    pass
