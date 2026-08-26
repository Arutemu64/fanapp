"""add outbox insert NOTIFY trigger

Wakes the outbox relay the instant an event is enqueued, instead of it waiting
out its poll interval. An ``AFTER INSERT`` trigger on ``outbox_events`` fires
``pg_notify('outbox_new', '')``; the relay ``LISTEN``s on that channel and
drains immediately (see ``adapters/db/outbox_signal.py``). The relay's periodic
poll stays the correctness backstop, so this only lowers latency — a missed
notification is never a lost event.

Statement-level (not row-level): one enqueue commit is one drain regardless of
how many rows it wrote, and an empty constant payload lets Postgres coalesce the
notifications of a single transaction into one delivery. ``NOTIFY`` is delivered
at COMMIT, so the listener only wakes once the rows are durably visible.

Hand-written: Alembic autogenerate neither emits nor diffs functions and
triggers, so this DDL and its teardown live here explicitly. The channel name
``outbox_new`` is a contract with ``OUTBOX_CHANNEL`` in the listener adapter —
change one, change both.

Revision ID: f1e2d3c4b5a6
Revises: e7f8a9b0c1d2
Create Date: 2026-08-26 10:00:00.000000

"""

from alembic import op

revision = "f1e2d3c4b5a6"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None

_FUNCTION = "outbox_notify"
_TRIGGER = "outbox_events_notify"
_TABLE = "outbox_events"
_CHANNEL = "outbox_new"


def upgrade() -> None:
    op.execute(
        f"""
        CREATE FUNCTION {_FUNCTION}() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            PERFORM pg_notify('{_CHANNEL}', '');
            RETURN NULL;
        END;
        $$;
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {_TRIGGER}
        AFTER INSERT ON {_TABLE}
        FOR EACH STATEMENT
        EXECUTE FUNCTION {_FUNCTION}();
        """
    )


def downgrade() -> None:
    op.execute(f"DROP TRIGGER IF EXISTS {_TRIGGER} ON {_TABLE}")
    op.execute(f"DROP FUNCTION IF EXISTS {_FUNCTION}()")
