"""rename_event_id_to_schedule_item_id

Revision ID: 6b6d0c521761
Revises: f3a9c1d72b48
Create Date: 2026-06-24 13:23:56.140681

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "6b6d0c521761"
down_revision = "f3a9c1d72b48"
branch_labels = None
depends_on = None


# Pure renames of the FK columns that point at the schedule (ScheduleItem) table,
# following the ScheduleEvent -> ScheduleItem entity rename. RENAME COLUMN /
# RENAME CONSTRAINT / RENAME INDEX preserve data and the underlying objects;
# the autogenerate drop+add version would have destroyed existing rows.
def upgrade() -> None:
    # subscriptions.event_id -> schedule_item_id
    op.alter_column("subscriptions", "event_id", new_column_name="schedule_item_id")
    op.execute(
        "ALTER TABLE subscriptions RENAME CONSTRAINT "
        "fk_subscriptions_event_id_schedule "
        "TO fk_subscriptions_schedule_item_id_schedule"
    )
    op.execute(
        "ALTER TABLE subscriptions RENAME CONSTRAINT "
        "uq_subscriptions_event_id TO uq_subscriptions_schedule_item_id"
    )

    # schedule_changes.changed_event_id / argument_event_id -> *_schedule_item_id
    op.alter_column(
        "schedule_changes",
        "changed_event_id",
        new_column_name="changed_schedule_item_id",
    )
    op.alter_column(
        "schedule_changes",
        "argument_event_id",
        new_column_name="argument_schedule_item_id",
    )
    op.execute(
        "ALTER TABLE schedule_changes RENAME CONSTRAINT "
        "fk_schedule_changes_changed_event_id_schedule "
        "TO fk_schedule_changes_changed_schedule_item_id_schedule"
    )
    op.execute(
        "ALTER TABLE schedule_changes RENAME CONSTRAINT "
        "fk_schedule_changes_argument_event_id_schedule "
        "TO fk_schedule_changes_argument_schedule_item_id_schedule"
    )
    op.execute(
        "ALTER INDEX ix_schedule_changes_changed_event_id "
        "RENAME TO ix_schedule_changes_changed_schedule_item_id"
    )
    op.execute(
        "ALTER INDEX ix_schedule_changes_argument_event_id "
        "RENAME TO ix_schedule_changes_argument_schedule_item_id"
    )


def downgrade() -> None:
    op.execute(
        "ALTER INDEX ix_schedule_changes_argument_schedule_item_id "
        "RENAME TO ix_schedule_changes_argument_event_id"
    )
    op.execute(
        "ALTER INDEX ix_schedule_changes_changed_schedule_item_id "
        "RENAME TO ix_schedule_changes_changed_event_id"
    )
    op.execute(
        "ALTER TABLE schedule_changes RENAME CONSTRAINT "
        "fk_schedule_changes_argument_schedule_item_id_schedule "
        "TO fk_schedule_changes_argument_event_id_schedule"
    )
    op.execute(
        "ALTER TABLE schedule_changes RENAME CONSTRAINT "
        "fk_schedule_changes_changed_schedule_item_id_schedule "
        "TO fk_schedule_changes_changed_event_id_schedule"
    )
    op.alter_column(
        "schedule_changes",
        "argument_schedule_item_id",
        new_column_name="argument_event_id",
    )
    op.alter_column(
        "schedule_changes",
        "changed_schedule_item_id",
        new_column_name="changed_event_id",
    )

    op.execute(
        "ALTER TABLE subscriptions RENAME CONSTRAINT "
        "uq_subscriptions_schedule_item_id TO uq_subscriptions_event_id"
    )
    op.execute(
        "ALTER TABLE subscriptions RENAME CONSTRAINT "
        "fk_subscriptions_schedule_item_id_schedule "
        "TO fk_subscriptions_event_id_schedule"
    )
    op.alter_column("subscriptions", "schedule_item_id", new_column_name="event_id")
