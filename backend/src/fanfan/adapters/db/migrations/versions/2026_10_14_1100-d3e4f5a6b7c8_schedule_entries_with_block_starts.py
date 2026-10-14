"""schedule entries with block starts

Turns ``schedule_events`` into ``schedule_entries``: a block is no longer a
``block_title`` repeated on each of its events but an entry of its own
(``kind = 'block_start'``) at the head of the block. An event belongs to the
nearest block start above it, so moving an event across one moves it between
blocks.

Postgres keeps old constraint/index/sequence names after a table rename, so each
is renamed to match the metadata naming convention (the subscriptions gateway
maps fk_subscriptions_event_id_schedule_entries to a domain error, so that name
must match).

The deployed table holds a real programme, so the backfill does not assume it is
empty: ``kind`` goes in with a server default that marks every existing row an
event, and one block start is inserted ahead of each run of consecutive rows
sharing a ``block_title`` — the same runs the schedule page grouped into block
sections. A blank title (NULL or whitespace) started no section there and starts
none here. One behaviour cannot carry over: a block-less row between two blocks
(a break) used to sit outside both and now belongs to the block above it.

Downgrade restores ``block_title`` on every event from its nearest block start
and drops the block starts. Schedule changes that recorded a move to the top of
a block reference that block start, so the cascade deletes them with it.

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-10-14 11:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d3e4f5a6b7c8"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None

_KIND_CHECK = "ck_schedule_entries_scheduleentrykind"
_BLOCK_START_CHECK = "ck_schedule_entries_block_start_has_no_stage_state"

# (table, old name, new name) for every constraint naming the renamed table.
_CONSTRAINT_RENAMES = (
    ("schedule_entries", "pk_schedule_events", "pk_schedule_entries"),
    ("schedule_entries", "uq_schedule_events_number", "uq_schedule_entries_number"),
    ("schedule_entries", "uq_schedule_events_order", "uq_schedule_entries_order"),
    (
        "subscriptions",
        "fk_subscriptions_event_id_schedule_events",
        "fk_subscriptions_event_id_schedule_entries",
    ),
    (
        "schedule_changes",
        "fk_schedule_changes_changed_event_id_schedule_events",
        "fk_schedule_changes_changed_event_id_schedule_entries",
    ),
    (
        "schedule_changes",
        "fk_schedule_changes_argument_event_id_schedule_events",
        "fk_schedule_changes_argument_event_id_schedule_entries",
    ),
)


def upgrade() -> None:
    op.rename_table("schedule_events", "schedule_entries")
    for table, old_name, new_name in _CONSTRAINT_RENAMES:
        op.execute(f"ALTER TABLE {table} RENAME CONSTRAINT {old_name} TO {new_name}")
    op.execute(
        "ALTER SEQUENCE schedule_events_order_seq RENAME TO schedule_entries_order_seq"
    )

    # The server default fills every existing row in one fast metadata-only
    # change (Postgres 11+), then goes: the app always states the kind.
    op.add_column(
        "schedule_entries",
        sa.Column("kind", sa.String(length=32), nullable=False, server_default="event"),
    )
    op.alter_column("schedule_entries", "kind", server_default=None)
    op.create_check_constraint(
        op.f(_KIND_CHECK),
        "schedule_entries",
        sa.column("kind").in_(["event", "block_start"]),
    )

    # A run starts wherever a row's block differs from the row above it. Its
    # block start takes an order halfway to the row above, which is free: order
    # is unique and nothing sits strictly between two neighbours.
    op.execute(
        """
        WITH ranked AS (
            SELECT
                "order",
                NULLIF(btrim(block_title), '') AS block,
                LAG(NULLIF(btrim(block_title), ''))
                    OVER (ORDER BY "order") AS previous_block,
                LAG("order") OVER (ORDER BY "order") AS previous_order
            FROM schedule_entries
        )
        INSERT INTO schedule_entries (id, kind, title, "order")
        SELECT
            uuidv7(),
            'block_start',
            block,
            CASE
                WHEN previous_order IS NULL THEN "order" - 1
                ELSE (previous_order + "order") / 2
            END
        FROM ranked
        WHERE block IS NOT NULL AND block IS DISTINCT FROM previous_block
        """
    )

    op.drop_column("schedule_entries", "block_title")
    op.create_check_constraint(
        op.f(_BLOCK_START_CHECK),
        "schedule_entries",
        "kind = 'event' OR "
        "(number IS NULL AND is_current IS FALSE AND is_skipped IS FALSE)",
    )


def downgrade() -> None:
    op.drop_constraint(op.f(_BLOCK_START_CHECK), "schedule_entries", type_="check")
    op.add_column(
        "schedule_entries", sa.Column("block_title", sa.String(), nullable=True)
    )
    op.execute(
        """
        UPDATE schedule_entries AS event
        SET block_title = (
            SELECT block.title
            FROM schedule_entries AS block
            WHERE block.kind = 'block_start' AND block."order" < event."order"
            ORDER BY block."order" DESC
            LIMIT 1
        )
        WHERE event.kind = 'event'
        """
    )
    op.execute("DELETE FROM schedule_entries WHERE kind = 'block_start'")
    op.drop_constraint(op.f(_KIND_CHECK), "schedule_entries", type_="check")
    op.drop_column("schedule_entries", "kind")

    op.execute(
        "ALTER SEQUENCE schedule_entries_order_seq RENAME TO schedule_events_order_seq"
    )
    for table, old_name, new_name in _CONSTRAINT_RENAMES:
        op.execute(f"ALTER TABLE {table} RENAME CONSTRAINT {new_name} TO {old_name}")
    op.rename_table("schedule_entries", "schedule_events")
