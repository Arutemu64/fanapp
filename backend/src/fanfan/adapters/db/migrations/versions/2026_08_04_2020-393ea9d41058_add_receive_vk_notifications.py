"""add_receive_vk_notifications

Revision ID: 393ea9d41058
Revises: b691d03eeef6
Create Date: 2026-08-04 20:20:36.738072

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "393ea9d41058"
down_revision = "b691d03eeef6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "receive_vk_notifications",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "receive_vk_notifications")
