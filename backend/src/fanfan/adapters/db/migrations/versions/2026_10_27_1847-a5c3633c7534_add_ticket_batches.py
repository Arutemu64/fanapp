"""add ticket_batches and tickets.batch_id

A new table and a nullable column, so existing tickets need no backfill:
imported and older tickets simply have no batch.

Revision ID: a5c3633c7534
Revises: 4b8e2d6f1a37
Create Date: 2026-10-27 18:47:47.847309

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a5c3633c7534"
down_revision = "4b8e2d6f1a37"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ticket_batches",
        sa.Column(
            "role",
            sa.Enum(
                "visitor",
                "participant",
                "volunteer",
                "organizer",
                name="userrole",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("issued_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["issued_by_user_id"],
            ["users.id"],
            name=op.f("fk_ticket_batches_issued_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ticket_batches")),
    )
    op.create_index(
        op.f("ix_ticket_batches_issued_by_user_id"),
        "ticket_batches",
        ["issued_by_user_id"],
        unique=False,
    )
    op.add_column("tickets", sa.Column("batch_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_tickets_batch_id"), "tickets", ["batch_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_tickets_batch_id_ticket_batches"),
        "tickets",
        "ticket_batches",
        ["batch_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_tickets_batch_id_ticket_batches"), "tickets", type_="foreignkey"
    )
    op.drop_index(op.f("ix_tickets_batch_id"), table_name="tickets")
    op.drop_column("tickets", "batch_id")
    op.drop_index(
        op.f("ix_ticket_batches_issued_by_user_id"), table_name="ticket_batches"
    )
    op.drop_table("ticket_batches")
