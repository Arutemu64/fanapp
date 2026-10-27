"""make the schedule event number optional

Not every row of the programme carries a public number: breaks and other filler
are announced by title alone, and the import spreadsheet now accepts an empty
``number`` cell for them.

``number`` keeps its unique index — Postgres treats NULLs as distinct there, so
any number of numberless events coexist while real numbers stay unique.

The downgrade restores ``NOT NULL`` and therefore fails while numberless events
exist; delete them (or give them numbers) first.

Revision ID: d877cbd8955e
Revises: b4d81f2ac907
Create Date: 2026-07-31 18:15:33.986368

"""

import sqlalchemy as sa
from alembic import op

revision = "d877cbd8955e"
down_revision = "b4d81f2ac907"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "schedule_events", "number", existing_type=sa.INTEGER(), nullable=True
    )


def downgrade() -> None:
    op.alter_column(
        "schedule_events", "number", existing_type=sa.INTEGER(), nullable=False
    )
