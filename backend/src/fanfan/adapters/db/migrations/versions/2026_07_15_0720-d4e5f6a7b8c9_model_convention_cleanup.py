"""model convention cleanup: rename outlier tables, drop noise updated_at

Renames two tables to match the plural, fully-spelled convention used by every
other table, and drops ``updated_at`` from append-only / audit tables where it
could never move.

- schedule       -> schedule_events   (class is ScheduleEventORM)
- push_subs      -> push_subscriptions (class is PushSubscriptionORM)

Postgres keeps old constraint/index/sequence names after a table rename, so each
is renamed explicitly to satisfy the metadata naming convention (the gateways map
uq_push_subscriptions_endpoint and fk_subscriptions_event_id_schedule_events to
domain errors, so those names must match).

``updated_at`` is dropped from tables that are only ever inserted into / deleted
from (never UPDATEd); ``created_at`` stays on every table.

Revision ID: d4e5f6a7b8c9
Revises: b70291fe7e46
Create Date: 2026-07-15 07:20:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "b70291fe7e46"
branch_labels = None
depends_on = None

# Tables that lose updated_at (append-only / audit — insert/delete only).
APPEND_ONLY_TABLES = (
    "votes",
    "feedback",
    "schedule_changes",
    "user_flags",
    "user_permissions",
    "push_subscriptions",
    "social_identities",
)


def upgrade() -> None:
    # --- schedule -> schedule_events -------------------------------------
    op.rename_table("schedule", "schedule_events")
    op.execute(
        "ALTER TABLE schedule_events RENAME CONSTRAINT pk_schedule TO pk_schedule_events"
    )
    op.execute(
        "ALTER TABLE schedule_events "
        "RENAME CONSTRAINT uq_schedule_number TO uq_schedule_events_number"
    )
    op.execute(
        "ALTER TABLE schedule_events "
        "RENAME CONSTRAINT uq_schedule_order TO uq_schedule_events_order"
    )
    op.execute("ALTER INDEX ix_schedule_title RENAME TO ix_schedule_events_title")
    op.execute("ALTER SEQUENCE schedule_order_seq RENAME TO schedule_events_order_seq")
    # Inbound FKs live on the referring tables and embed the referred table name.
    op.execute(
        "ALTER TABLE subscriptions "
        "RENAME CONSTRAINT fk_subscriptions_event_id_schedule "
        "TO fk_subscriptions_event_id_schedule_events"
    )
    op.execute(
        "ALTER TABLE schedule_changes "
        "RENAME CONSTRAINT fk_schedule_changes_changed_event_id_schedule "
        "TO fk_schedule_changes_changed_event_id_schedule_events"
    )
    op.execute(
        "ALTER TABLE schedule_changes "
        "RENAME CONSTRAINT fk_schedule_changes_argument_event_id_schedule "
        "TO fk_schedule_changes_argument_event_id_schedule_events"
    )

    # --- push_subs -> push_subscriptions ---------------------------------
    op.rename_table("push_subs", "push_subscriptions")
    op.execute(
        "ALTER TABLE push_subscriptions "
        "RENAME CONSTRAINT pk_push_subs TO pk_push_subscriptions"
    )
    op.execute(
        "ALTER TABLE push_subscriptions "
        "RENAME CONSTRAINT uq_push_subs_endpoint TO uq_push_subscriptions_endpoint"
    )
    op.execute(
        "ALTER TABLE push_subscriptions "
        "RENAME CONSTRAINT fk_push_subs_user_id_users "
        "TO fk_push_subscriptions_user_id_users"
    )
    op.execute(
        "ALTER INDEX ix_push_subs_user_id RENAME TO ix_push_subscriptions_user_id"
    )

    # --- drop noise updated_at from append-only tables -------------------
    for table in APPEND_ONLY_TABLES:
        op.drop_column(table, "updated_at")


def downgrade() -> None:
    # Re-add updated_at (existing rows get now() via the server default).
    for table in APPEND_ONLY_TABLES:
        op.add_column(
            table,
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )

    # --- push_subscriptions -> push_subs ---------------------------------
    op.execute(
        "ALTER INDEX ix_push_subscriptions_user_id RENAME TO ix_push_subs_user_id"
    )
    op.execute(
        "ALTER TABLE push_subscriptions "
        "RENAME CONSTRAINT fk_push_subscriptions_user_id_users "
        "TO fk_push_subs_user_id_users"
    )
    op.execute(
        "ALTER TABLE push_subscriptions "
        "RENAME CONSTRAINT uq_push_subscriptions_endpoint TO uq_push_subs_endpoint"
    )
    op.execute(
        "ALTER TABLE push_subscriptions "
        "RENAME CONSTRAINT pk_push_subscriptions TO pk_push_subs"
    )
    op.rename_table("push_subscriptions", "push_subs")

    # --- schedule_events -> schedule -------------------------------------
    op.execute(
        "ALTER TABLE schedule_changes "
        "RENAME CONSTRAINT fk_schedule_changes_argument_event_id_schedule_events "
        "TO fk_schedule_changes_argument_event_id_schedule"
    )
    op.execute(
        "ALTER TABLE schedule_changes "
        "RENAME CONSTRAINT fk_schedule_changes_changed_event_id_schedule_events "
        "TO fk_schedule_changes_changed_event_id_schedule"
    )
    op.execute(
        "ALTER TABLE subscriptions "
        "RENAME CONSTRAINT fk_subscriptions_event_id_schedule_events "
        "TO fk_subscriptions_event_id_schedule"
    )
    op.execute("ALTER SEQUENCE schedule_events_order_seq RENAME TO schedule_order_seq")
    op.execute("ALTER INDEX ix_schedule_events_title RENAME TO ix_schedule_title")
    op.execute(
        "ALTER TABLE schedule_events "
        "RENAME CONSTRAINT uq_schedule_events_order TO uq_schedule_order"
    )
    op.execute(
        "ALTER TABLE schedule_events "
        "RENAME CONSTRAINT uq_schedule_events_number TO uq_schedule_number"
    )
    op.execute(
        "ALTER TABLE schedule_events RENAME CONSTRAINT pk_schedule_events TO pk_schedule"
    )
    op.rename_table("schedule_events", "schedule")
