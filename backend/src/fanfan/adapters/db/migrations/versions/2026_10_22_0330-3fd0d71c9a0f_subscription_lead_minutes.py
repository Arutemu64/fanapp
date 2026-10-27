"""Remind subscribers by minutes, once, in a push lane per act

Revision ID: 3fd0d71c9a0f
Revises: e4b7c2a9d1f3
Create Date: 2026-10-22 03:30:44.522708

"""

import sqlalchemy as sa
from alembic import op

revision = "3fd0d71c9a0f"
down_revision = "e4b7c2a9d1f3"
branch_labels = None
depends_on = None

DEFAULT_LEAD_MINUTES = 15
DEFAULT_COUNTER = 5


def upgrade() -> None:
    op.add_column("notifications", sa.Column("event_id", sa.Uuid(), nullable=True))

    op.add_column(
        "subscriptions", sa.Column("lead_minutes", sa.Integer(), nullable=True)
    )
    op.execute(
        sa.text("UPDATE subscriptions SET lead_minutes = :lead_minutes").bindparams(
            lead_minutes=DEFAULT_LEAD_MINUTES
        )
    )
    op.alter_column("subscriptions", "lead_minutes", nullable=False)
    op.drop_column("subscriptions", "counter")

    op.add_column(
        "subscriptions", sa.Column("reminded_by_change_id", sa.Uuid(), nullable=True)
    )
    op.create_index(
        op.f("ix_subscriptions_reminded_by_change_id"),
        "subscriptions",
        ["reminded_by_change_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_subscriptions_reminded_by_change_id_schedule_changes"),
        "subscriptions",
        "schedule_changes",
        ["reminded_by_change_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.alter_column(
        "users",
        "receive_all_announcements",
        existing_type=sa.BOOLEAN(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "receive_all_announcements",
        existing_type=sa.BOOLEAN(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    op.drop_constraint(
        op.f("fk_subscriptions_reminded_by_change_id_schedule_changes"),
        "subscriptions",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_subscriptions_reminded_by_change_id"), table_name="subscriptions"
    )
    op.drop_column("subscriptions", "reminded_by_change_id")

    op.add_column(
        "subscriptions",
        sa.Column("counter", sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.execute(
        sa.text("UPDATE subscriptions SET counter = :counter").bindparams(
            counter=DEFAULT_COUNTER
        )
    )
    op.alter_column("subscriptions", "counter", nullable=False)
    op.drop_column("subscriptions", "lead_minutes")

    op.drop_column("notifications", "event_id")
