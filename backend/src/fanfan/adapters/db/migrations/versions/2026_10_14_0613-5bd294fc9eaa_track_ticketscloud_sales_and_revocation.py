"""track_ticketscloud_sales_and_revocation

Revision ID: 5bd294fc9eaa
Revises: 03832aef92cd
Create Date: 2026-10-14 06:13:36.040198

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5bd294fc9eaa"
down_revision = "03832aef92cd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Both columns stay nullable: existing rows have no order id to backfill
    # from SQL (it lives only in TicketsCloud), so the next ticket sync fills it
    # in by matching each row's barcode. Tickets issued by organizers never
    # have one. NULLs are distinct, so the new sale constraint holds for every
    # existing row.
    op.add_column(
        "tickets", sa.Column("ticketscloud_order_id", sa.String(), nullable=True)
    )
    op.add_column(
        "tickets", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True)
    )
    # TicketsCloud sells a refunded ticket id again under a new order, so the
    # ticket id alone no longer identifies a row; the lookup index replaces it.
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
    # Fails once a resold ticket id has been imported twice. That is correct:
    # the old schema cannot hold both sales, and which one to drop is a human
    # decision.
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
