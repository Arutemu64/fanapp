"""track_ticketscloud_sales_and_revocation

Revision ID: 5bd294fc9eaa
Revises: 03832aef92cd
Create Date: 2026-10-14 06:13:36.040198

"""

import sqlalchemy as sa
from alembic import op

revision = "5bd294fc9eaa"
down_revision = "03832aef92cd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tickets", sa.Column("ticketscloud_order_id", sa.String(), nullable=True)
    )
    op.add_column(
        "tickets", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.drop_constraint(
        op.f("uq_tickets_ticketscloud_ticket_id"), "tickets", type_="unique"
    )
    op.create_index(
        op.f("ix_tickets_ticketscloud_ticket_id"),
        "tickets",
        ["ticketscloud_ticket_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_tickets_ticketscloud_sale",
        "tickets",
        ["ticketscloud_order_id", "ticketscloud_ticket_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_tickets_ticketscloud_sale", "tickets", type_="unique")
    op.drop_index(op.f("ix_tickets_ticketscloud_ticket_id"), table_name="tickets")
    op.create_unique_constraint(
        op.f("uq_tickets_ticketscloud_ticket_id"),
        "tickets",
        ["ticketscloud_ticket_id"],
        postgresql_nulls_not_distinct=False,
    )
    op.drop_column("tickets", "revoked_at")
    op.drop_column("tickets", "ticketscloud_order_id")
