"""add sync_runs

Records every vendor sync (Cosplay2 / TicketsCloud) from every trigger — the
web button, cron and the CLI — so "last synced" reflects reality rather than
only the last manual run.

``uq_sync_runs_active`` is a *partial* unique index on ``source`` restricted to
``finished_at IS NULL``: at most one unfinished run per source. It is the
concurrency guard (a manual sync can't overlap a scheduled one and double-sweep
the vendor API) and doubles as the "is a run active?" signal the UI reads to
disable the button.

Revision ID: 0f25d74d8716
Revises: a1b2c3d4e5f6
Create Date: 2026-07-25 12:10:19.587401

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0f25d74d8716"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sync_runs",
        sa.Column(
            "source",
            sa.Enum(
                "cosplay2",
                "tcloud",
                name="syncsource",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "finished",
                "failed",
                name="syncrunstatus",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("by_user_id", sa.Uuid(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["by_user_id"],
            ["users.id"],
            name=op.f("fk_sync_runs_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sync_runs")),
    )
    op.create_index(
        op.f("ix_sync_runs_by_user_id"), "sync_runs", ["by_user_id"], unique=False
    )
    op.create_index(
        "uq_sync_runs_active",
        "sync_runs",
        ["source"],
        unique=True,
        postgresql_where="finished_at IS NULL",
    )


def downgrade() -> None:
    op.drop_index(
        "uq_sync_runs_active",
        table_name="sync_runs",
        postgresql_where="finished_at IS NULL",
    )
    op.drop_index(op.f("ix_sync_runs_by_user_id"), table_name="sync_runs")
    op.drop_table("sync_runs")
