"""enable pg_stat_statements

Query statistics for index and tuning decisions. The views work only once the
server preloads the module (shared_preload_libraries in docker-compose.yml);
CREATE EXTENSION succeeds either way. See docs/deployment.md.

Revision ID: c3e1d7a2b9f4
Revises: 387a84885244
Create Date: 2026-10-28 05:10:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c3e1d7a2b9f4"
down_revision = "387a84885244"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pg_stat_statements")
