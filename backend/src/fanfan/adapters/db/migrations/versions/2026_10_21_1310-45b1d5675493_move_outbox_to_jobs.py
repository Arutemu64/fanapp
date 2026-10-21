"""move_outbox_to_jobs

Retires the transactional outbox (ADR-0004, ADR-0015) now that messages are
queued as Procrastinate jobs in the producing transaction itself (ADR-0041).

Undelivered rows are not dropped: each becomes one job per task subscribed to
its subject, with the payload, commit time and trace headers it carried, so a
deploy that lands while the relay is behind loses nothing. Delivered rows are
history and go with the table.

Revision ID: 45b1d5675493
Revises: e9c2a8d22f17
Create Date: 2026-10-21 13:10:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "45b1d5675493"
down_revision = "e9c2a8d22f17"
branch_labels = None
depends_on = None

# Subject → subscribed task names, as the worker registers them at this
# revision (presentation/worker). Spelled out rather than imported: a migration
# must not change when the code it was written against does.
_ROUTES = (
    ("cmd.notifications.create", "notifications:create_new_notification"),
    ("notifications.created", "notifications:send_notification_to_telegram"),
    ("notifications.created", "notifications:send_notification_to_vk"),
    ("notifications.created", "notifications:send_push_notification"),
    ("cmd.notifications.broadcast.process", "notifications:create_new_broadcast"),
    ("cmd.notifications.mailing.cancel", "notifications:cancel_mailing"),
    ("schedule.change.created", "schedule:process_schedule_change"),
    ("schedule.change.undone", "schedule:undo_schedule_change"),
    ("cmd.sync.run", "sync:run_requested_sync"),
)
_QUEUE = "default"

# Left in place by the add_outbox_insert_notify_trigger revision.
_NOTIFY_FUNCTION = "outbox_notify"
_NOTIFY_TRIGGER = "outbox_events_notify"
_NOTIFY_CHANNEL = "outbox_new"


def upgrade() -> None:
    op.execute(
        "CREATE TEMPORARY TABLE outbox_routes (subject text, task_name text, ord int)"
    )
    routes_table = sa.table(
        "outbox_routes",
        sa.column("subject", sa.Text()),
        sa.column("task_name", sa.Text()),
        sa.column("ord", sa.Integer()),
    )
    op.bulk_insert(
        routes_table,
        [
            {"subject": subject, "task_name": task, "ord": order}
            for order, (subject, task) in enumerate(_ROUTES)
        ],
    )
    # An undelivered row no task subscribes to would vanish with the table.
    # None should exist (earlier revisions renamed or retired every old
    # subject), so finding one stops the deploy for a human to look at rather
    # than dropping it unseen.
    op.execute(
        """
        DO $$
        DECLARE unrouted text;
        BEGIN
            SELECT string_agg(DISTINCT o.subject, ', ') INTO unrouted
            FROM outbox_events o
            WHERE o.published_at IS NULL
              AND o.subject NOT IN (SELECT subject FROM outbox_routes);
            IF unrouted IS NOT NULL THEN
                RAISE EXCEPTION 'Undelivered outbox rows with no task: %', unrouted;
            END IF;
        END;
        $$;
        """
    )
    # The same row shape procrastinate_defer_jobs_v1 inserts, and the same
    # arguments the job queue adapter writes (adapters/procrastinate).
    op.execute(
        sa.text(
            """
            INSERT INTO procrastinate_jobs (queue_name, task_name, args)
            SELECT
                :queue,
                r.task_name,
                jsonb_build_object(
                    'message', o.payload,
                    'occurred_at', to_jsonb(o.created_at),
                    'trace_headers', o.trace_headers
                )
            FROM outbox_events o
            JOIN outbox_routes r ON r.subject = o.subject
            WHERE o.published_at IS NULL
            ORDER BY o.created_at, o.id, r.ord
            """
        ).bindparams(queue=_QUEUE)
    )
    op.execute("DROP TABLE outbox_routes")
    op.execute(f"DROP TRIGGER IF EXISTS {_NOTIFY_TRIGGER} ON outbox_events")
    op.execute(f"DROP FUNCTION IF EXISTS {_NOTIFY_FUNCTION}()")
    op.drop_table("outbox_events")


def downgrade() -> None:
    # Restores the empty table and its wake-up trigger. Jobs queued since stay
    # in Procrastinate's tables: the relay this would bring back cannot read
    # them, and the worker that can is gone with the downgrade.
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "attempts", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "trace_headers", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_events")),
    )
    op.create_index(
        "ix_outbox_events_unpublished",
        "outbox_events",
        ["created_at"],
        unique=False,
        postgresql_where="published_at IS NULL",
    )
    op.create_index(
        "ix_outbox_events_published_at",
        "outbox_events",
        ["published_at"],
        unique=False,
    )
    op.execute(
        f"""
        CREATE FUNCTION {_NOTIFY_FUNCTION}() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            PERFORM pg_notify('{_NOTIFY_CHANNEL}', '');
            RETURN NULL;
        END;
        $$;
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {_NOTIFY_TRIGGER}
        AFTER INSERT ON outbox_events
        FOR EACH STATEMENT
        EXECUTE FUNCTION {_NOTIFY_FUNCTION}();
        """
    )
