"""add_votes_nomination_uniqueness

Revision ID: b8575c07d24a
Revises: a7b8c9d0e1f2
Create Date: 2026-09-05 22:45:38.158959

"""

import sqlalchemy as sa
from alembic import op

revision = "b8575c07d24a"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("votes", sa.Column("nomination_id", sa.Uuid(), nullable=True))
    op.execute(
        """
        UPDATE votes
        SET nomination_id = participants.nomination_id
        FROM participants
        WHERE votes.participant_id = participants.id
        """
    )
    op.alter_column("votes", "nomination_id", nullable=False)
    op.create_index(
        op.f("ix_votes_nomination_id"), "votes", ["nomination_id"], unique=False
    )
    op.create_unique_constraint(
        "uq_votes_user_nomination", "votes", ["user_id", "nomination_id"]
    )
    op.create_foreign_key(
        op.f("fk_votes_nomination_id_nominations"),
        "votes",
        "nominations",
        ["nomination_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_votes_nomination_id_nominations"), "votes", type_="foreignkey"
    )
    op.drop_constraint("uq_votes_user_nomination", "votes", type_="unique")
    op.drop_index(op.f("ix_votes_nomination_id"), table_name="votes")
    op.drop_column("votes", "nomination_id")
