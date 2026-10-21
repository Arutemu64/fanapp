"""drop_outbox

Retires the transactional outbox (ADR-0004, ADR-0015) now that messages are
queued as Procrastinate jobs in the producing transaction itself (ADR-0041).
The app is not live yet, so its rows are dropped rather than moved.

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

# Left in place by the add_outbox_insert_notify_trigger revision.
_NOTIFY_FUNCTION = "outbox_notify"
_NOTIFY_TRIGGER = "outbox_events_notify"
_NOTIFY_CHANNEL = "outbox_new"


def upgrade() -> None:
    op.execute(f"DROP TRIGGER IF EXISTS {_NOTIFY_TRIGGER} ON outbox_events")
    op.execute(f"DROP FUNCTION IF EXISTS {_NOTIFY_FUNCTION}()")
    op.drop_table("outbox_events")


def downgrade() -> None:
    # Restores the empty table and its wake-up trigger.
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
