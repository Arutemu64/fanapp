"""add users.avatar_seed

Adds the per-user seed the client feeds to the DiceBear avatar generator.

The table holds real rows, so the column goes in nullable, existing users get a
random seed from an explicit ``UPDATE``, and only then is it tightened to
``NOT NULL``. ``md5(random() || id)`` yields 12 hex characters, which satisfies
``AVATAR_SEED_PATTERN`` without needing the ``pgcrypto`` extension.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-10-14 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_seed", sa.String(), nullable=True))
    op.execute(
        "UPDATE users SET avatar_seed = substr(md5(random()::text || id::text), 1, 12)"
    )
    op.alter_column("users", "avatar_seed", nullable=False)


def downgrade() -> None:
    op.drop_column("users", "avatar_seed")
