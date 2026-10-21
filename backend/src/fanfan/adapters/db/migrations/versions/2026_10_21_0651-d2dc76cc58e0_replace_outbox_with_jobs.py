"""replace outbox with jobs

The transactional outbox becomes the job queue itself: instead of a relay
copying each event to NATS for FastStream consumers, the worker claims one
``jobs`` row per handler of an event and runs it (ADR-0040).

``outbox_events`` is dropped with whatever it still holds, deliberately: the
change ships with no backward compatibility, so undelivered rows and anything
left in the NATS stream are abandoned rather than drained (the deploy notes
say so). In practice the table holds only delivered rows awaiting retention.

The NOTIFY trigger moves with it, from ``outbox_new`` to ``jobs_new`` — the
channel is a contract with ``JOBS_CHANNEL`` in ``adapters/db/job_signal.py``.
Autogenerate neither emits nor diffs functions and triggers, so that DDL is
hand-written below.

Revision ID: d2dc76cc58e0
Revises: a325f3ea2dbc
Create Date: 2026-10-21 06:51:48.638356

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d2dc76cc58e0"
down_revision = "a325f3ea2dbc"
branch_labels = None
depends_on = None

_OUTBOX_FUNCTION = "outbox_notify"
_OUTBOX_TRIGGER = "outbox_events_notify"
_OUTBOX_CHANNEL = "outbox_new"
_JOBS_FUNCTION = "jobs_notify"
_JOBS_TRIGGER = "jobs_notify"
_JOBS_CHANNEL = "jobs_new"


def _create_notify_trigger(
    table: str, function: str, trigger: str, channel: str
) -> None:
    # Statement-level: one enqueue commit is one wake however many rows it
    # wrote, and the constant payload lets Postgres coalesce a transaction's
    # notifications into one delivery, sent at COMMIT.
    op.execute(
        f"""
        CREATE FUNCTION {function}() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            PERFORM pg_notify('{channel}', '');
            RETURN NULL;
        END;
        $$;
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {trigger}
        AFTER INSERT ON {table}
        FOR EACH STATEMENT
        EXECUTE FUNCTION {function}();
        """
    )


def _drop_notify_trigger(table: str, function: str, trigger: str) -> None:
    op.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
    op.execute(f"DROP FUNCTION IF EXISTS {function}()")


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "done",
                "discarded",
                "failed",
                name="jobstatus",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "run_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "attempts", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "trace_headers", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index("ix_jobs_finished_at", "jobs", ["finished_at"], unique=False)
    op.create_index(
        "ix_jobs_pending_run_at",
        "jobs",
        ["run_at"],
        unique=False,
        postgresql_where="status = 'pending'",
    )
    _create_notify_trigger("jobs", _JOBS_FUNCTION, _JOBS_TRIGGER, _JOBS_CHANNEL)

    _drop_notify_trigger("outbox_events", _OUTBOX_FUNCTION, _OUTBOX_TRIGGER)
    op.drop_index(op.f("ix_outbox_events_published_at"), table_name="outbox_events")
    op.drop_index(
        op.f("ix_outbox_events_unpublished"),
        table_name="outbox_events",
        postgresql_where="(published_at IS NULL)",
    )
    op.drop_table("outbox_events")


def downgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column("subject", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "published_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "attempts",
            sa.INTEGER(),
            server_default=sa.text("0"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "next_attempt_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("last_error", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "trace_headers",
            postgresql.JSONB(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_events")),
    )
    op.create_index(
        op.f("ix_outbox_events_unpublished"),
        "outbox_events",
        ["created_at"],
        unique=False,
        postgresql_where="(published_at IS NULL)",
    )
    op.create_index(
        op.f("ix_outbox_events_published_at"),
        "outbox_events",
        ["published_at"],
        unique=False,
    )
    _create_notify_trigger(
        "outbox_events", _OUTBOX_FUNCTION, _OUTBOX_TRIGGER, _OUTBOX_CHANNEL
    )

    _drop_notify_trigger("jobs", _JOBS_FUNCTION, _JOBS_TRIGGER)
    op.drop_index(
        "ix_jobs_pending_run_at",
        table_name="jobs",
        postgresql_where="status = 'pending'",
    )
    op.drop_index("ix_jobs_finished_at", table_name="jobs")
    op.drop_table("jobs")
