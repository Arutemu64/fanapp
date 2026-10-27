"""add_user_number

Revision ID: a325f3ea2dbc
Revises: f7bfa0725510
Create Date: 2026-10-20 09:10:13.781016

"""

import sqlalchemy as sa
from alembic import op

revision = "a325f3ea2dbc"
down_revision = "f7bfa0725510"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("number", sa.Integer(), nullable=True))
    op.execute(
        """
        WITH pool AS (
            SELECT n, row_number() OVER (ORDER BY random()) AS rn
            FROM generate_series(100000, 999999) AS n
        ),
        dealt AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn
            FROM users
        )
        UPDATE users
        SET number = pool.n
        FROM dealt
        JOIN pool ON pool.rn = dealt.rn
        WHERE users.id = dealt.id
        """
    )
    op.alter_column("users", "number", nullable=False)
    op.create_unique_constraint(op.f("uq_users_number"), "users", ["number"])


def downgrade() -> None:
    op.drop_constraint(op.f("uq_users_number"), "users", type_="unique")
    op.drop_column("users", "number")
