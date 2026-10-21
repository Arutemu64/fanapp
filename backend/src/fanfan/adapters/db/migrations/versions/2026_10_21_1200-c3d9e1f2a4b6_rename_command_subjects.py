"""rename_command_subjects

Revision ID: c3d9e1f2a4b6
Revises: a325f3ea2dbc
Create Date: 2026-10-21 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c3d9e1f2a4b6"
down_revision = "a325f3ea2dbc"
branch_labels = None
depends_on = None

# Commands left the domain-event subjects for their own `cmd.` prefix
# (ADR-0040). Spelled out rather than imported: a migration must not change when
# the code it was written against does. The payloads are unchanged, so only the
# subject moves.
_RENAMES = [
    ("notifications.queued", "cmd.notifications.create"),
    ("notifications.broadcast.queued", "cmd.notifications.broadcast.process"),
    ("notifications.mailing.cancelled", "cmd.notifications.mailing.cancel"),
    ("sync.requested", "cmd.sync.run"),
]


def _rename(old: str, new: str) -> None:
    # Only undelivered rows: the relay publishes a row under its stored subject,
    # and after this deploy no consumer listens on the old one, so an old-named
    # row would retry forever. Delivered rows are history the purge job drops.
    op.execute(
        sa.text(
            "UPDATE outbox_events SET subject = :new "
            "WHERE subject = :old AND published_at IS NULL"
        ).bindparams(old=old, new=new)
    )


def upgrade() -> None:
    for old, new in _RENAMES:
        _rename(old, new)


def downgrade() -> None:
    for old, new in _RENAMES:
        _rename(new, old)
