"""give mailing counters a DB-side default

sent_count / total_count are NOT NULL but previously carried only a Python-side
default (default=0), so an insert that bypasses the ORM's default handling (raw
SQL, a data migration, another service) would violate NOT NULL. Add a DB-level
default so the constraint is enforceable everywhere — matching duration and the
other counters.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-15 07:30:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE mailings ALTER COLUMN sent_count SET DEFAULT 0")
    op.execute("ALTER TABLE mailings ALTER COLUMN total_count SET DEFAULT 0")


def downgrade() -> None:
    op.execute("ALTER TABLE mailings ALTER COLUMN total_count DROP DEFAULT")
    op.execute("ALTER TABLE mailings ALTER COLUMN sent_count DROP DEFAULT")
