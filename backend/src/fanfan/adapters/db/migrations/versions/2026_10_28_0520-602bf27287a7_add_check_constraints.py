"""add check constraints mirroring domain invariants

Each constraint is added NOT VALID, then validated: the add holds its lock only
briefly, and VALIDATE scans the table without blocking writes. If VALIDATE
fails, a row already breaks the invariant; that is bad data for a human to
fix, not a reason to loosen the constraint.

Revision ID: 602bf27287a7
Revises: c3e1d7a2b9f4
Create Date: 2026-10-28 05:20:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "602bf27287a7"
down_revision = "c3e1d7a2b9f4"
branch_labels = None
depends_on = None

# (table, constraint name, condition)
CHECKS = [
    ("mailings", "ck_mailings_total_count_not_negative", "total_count >= 0"),
    ("outbox_events", "ck_outbox_events_attempts_not_negative", "attempts >= 0"),
    (
        "quest_awards",
        "ck_quest_awards_cancelled_by_has_cancelled_at",
        "cancelled_by IS NULL OR cancelled_at IS NOT NULL",
    ),
    ("rate_limits", "ck_rate_limits_hits_positive", "hits > 0"),
    ("schedule", "ck_schedule_duration_not_negative", "duration >= 0"),
    ("subscriptions", "ck_subscriptions_lead_minutes_positive", "lead_minutes > 0"),
    ("ticket_batches", "ck_ticket_batches_amount_positive", "amount > 0"),
    ("users", "ck_users_email_normalized", "email = lower(btrim(email))"),
]


def upgrade() -> None:
    for table, name, condition in CHECKS:
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({condition}) NOT VALID"
        )
        op.execute(f"ALTER TABLE {table} VALIDATE CONSTRAINT {name}")


def downgrade() -> None:
    for table, name, _ in reversed(CHECKS):
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {name}")
