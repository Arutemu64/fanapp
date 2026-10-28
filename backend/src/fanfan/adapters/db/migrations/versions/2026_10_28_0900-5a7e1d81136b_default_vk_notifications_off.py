"""default vk notifications off

VK notifications now turn on only after the user lets the community write, so a
new account starts with them off. Existing rows keep their value; a send VK
refuses switches them off.

Revision ID: 5a7e1d81136b
Revises: f9bb80dd4a6f
Create Date: 2026-10-28 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "5a7e1d81136b"
down_revision = "f9bb80dd4a6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users", "receive_vk_notifications", server_default=sa.text("false")
    )


def downgrade() -> None:
    op.alter_column("users", "receive_vk_notifications", server_default=sa.text("true"))
