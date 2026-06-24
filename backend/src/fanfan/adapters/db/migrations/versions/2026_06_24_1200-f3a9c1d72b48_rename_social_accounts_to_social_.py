"""rename social_accounts to social_identities

Revision ID: f3a9c1d72b48
Revises: 50bc789635be
Create Date: 2026-06-24 12:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f3a9c1d72b48"
down_revision = "50bc789635be"
branch_labels = None
depends_on = None


# Pure rename: the table and its constraints/indexes are renamed to match the
# "social identity" domain term. Postgres keeps old constraint/index names after
# a table rename, so each is renamed explicitly to satisfy the metadata naming
# convention (the gateway maps uq_social_identities_provider to a domain error).
def upgrade() -> None:
    op.rename_table("social_accounts", "social_identities")
    op.execute(
        "ALTER INDEX ix_social_accounts_user_id RENAME TO ix_social_identities_user_id"
    )
    op.execute(
        "ALTER TABLE social_identities "
        "RENAME CONSTRAINT pk_social_accounts TO pk_social_identities"
    )
    op.execute(
        "ALTER TABLE social_identities "
        "RENAME CONSTRAINT fk_social_accounts_user_id_users "
        "TO fk_social_identities_user_id_users"
    )
    op.execute(
        "ALTER TABLE social_identities "
        "RENAME CONSTRAINT uq_social_accounts_provider "
        "TO uq_social_identities_provider"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE social_identities "
        "RENAME CONSTRAINT uq_social_identities_provider "
        "TO uq_social_accounts_provider"
    )
    op.execute(
        "ALTER TABLE social_identities "
        "RENAME CONSTRAINT fk_social_identities_user_id_users "
        "TO fk_social_accounts_user_id_users"
    )
    op.execute(
        "ALTER TABLE social_identities "
        "RENAME CONSTRAINT pk_social_identities TO pk_social_accounts"
    )
    op.execute(
        "ALTER INDEX ix_social_identities_user_id RENAME TO ix_social_accounts_user_id"
    )
    op.rename_table("social_identities", "social_accounts")
