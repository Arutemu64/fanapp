"""name unique constraints after all their columns, index quest_awards.cancelled_by,
drop users.settings

The uq naming convention now spells every column (column_0_N_name), so two
multi-column constraints that share a first column no longer collide. Each
existing constraint is renamed in place: RENAME CONSTRAINT also renames its
backing index and never rebuilds it.

users.settings was written as {} and never read; the user's settings live in
their own columns.

Revision ID: 387a84885244
Revises: f9bb80dd4a6f
Create Date: 2026-10-28 04:59:14.658044

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "387a84885244"
down_revision = "f9bb80dd4a6f"
branch_labels = None
depends_on = None

# (table, old name, new name)
RENAMES = [
    (
        "participants",
        "uq_participants_nomination_id",
        "uq_participants_nomination_id_voting_number",
    ),
    (
        "social_identities",
        "uq_social_identities_provider",
        "uq_social_identities_provider_subject",
    ),
    (
        "social_identities",
        "uq_social_identities_user_id",
        "uq_social_identities_user_id_provider",
    ),
    ("subscriptions", "uq_subscriptions_event_id", "uq_subscriptions_event_id_user_id"),
    (
        "tickets",
        "uq_tickets_ticketscloud_sale",
        "uq_tickets_ticketscloud_order_id_ticketscloud_ticket_id",
    ),
    ("user_flags", "uq_user_flags_user_id", "uq_user_flags_user_id_name"),
    (
        "user_permissions",
        "uq_user_permissions_user_id",
        "uq_user_permissions_user_id_permission",
    ),
    ("votes", "uq_votes_user_id", "uq_votes_user_id_participant_id"),
    ("votes", "uq_votes_user_nomination", "uq_votes_user_id_nomination_id"),
]


def _rename(table: str, old: str, new: str) -> None:
    op.execute(f'ALTER TABLE {table} RENAME CONSTRAINT "{old}" TO "{new}"')


def upgrade() -> None:
    for table, old, new in RENAMES:
        _rename(table, old, new)
    op.create_index(
        op.f("ix_quest_awards_cancelled_by"),
        "quest_awards",
        ["cancelled_by"],
        unique=False,
    )
    op.drop_column("users", "settings")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.alter_column("users", "settings", server_default=None)
    op.drop_index(op.f("ix_quest_awards_cancelled_by"), table_name="quest_awards")
    for table, old, new in reversed(RENAMES):
        _rename(table, new, old)
