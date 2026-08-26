"""replace voting_enabled with voting_start/voting_end in app_settings JSONB

The voting toggle (a boolean ``voting_enabled``) is replaced by a time range
(``voting_start`` / ``voting_end`` datetimes). The AppSettings aggregate is
stored as a JSONB ``config`` column, so this is a data-only migration — no
DDL, just a key swap inside the JSON blob.

Revision ID: a1b2c3d4e5f7
Revises: e7f8a9b0c1d2
Create Date: 2026-08-26 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f7"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove the old ``voting_enabled`` key and add the new
    # ``voting_start`` / ``voting_end`` keys (both null = closed).
    op.execute(
        sa.text(
            """
            UPDATE app_settings
            SET config = (config - 'voting_enabled')
                || '{"voting_start": null, "voting_end": null}'::jsonb
            WHERE config ? 'voting_enabled'
            """
        )
    )


def downgrade() -> None:
    # Restore the boolean flag; any existing time range is lost.
    op.execute(
        sa.text(
            """
            UPDATE app_settings
            SET config = (config - 'voting_start' - 'voting_end')
                || '{"voting_enabled": false}'::jsonb
            WHERE config ? 'voting_start'
            """
        )
    )
