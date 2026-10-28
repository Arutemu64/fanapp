"""rename schedule.duration to duration_seconds

The column name now says its unit, like the API field it feeds.

Revision ID: 3c1d9e7a4b52
Revises: 5a7e1d81136b
Create Date: 2026-10-28 12:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "3c1d9e7a4b52"
down_revision = "5a7e1d81136b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("schedule", "duration", new_column_name="duration_seconds")


def downgrade() -> None:
    op.alter_column("schedule", "duration_seconds", new_column_name="duration")
