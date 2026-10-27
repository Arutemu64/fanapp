"""add_nomination_works_url

Revision ID: e115fa5e6481
Revises: ab92f36d626c
Create Date: 2026-06-13 23:16:24.832910

"""

import sqlalchemy as sa
from alembic import op

revision = "e115fa5e6481"
down_revision = "ab92f36d626c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("nominations", sa.Column("works_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("nominations", "works_url")
