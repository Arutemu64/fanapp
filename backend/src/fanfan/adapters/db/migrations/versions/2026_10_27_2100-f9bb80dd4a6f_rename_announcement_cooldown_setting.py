"""rename limits.announcement_timeout to announcement_cooldown_seconds

The settings row is one JSONB document, so the rename is a key move inside it.

Revision ID: f9bb80dd4a6f
Revises: a5c3633c7534
Create Date: 2026-10-27 21:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f9bb80dd4a6f"
down_revision = "a5c3633c7534"
branch_labels = None
depends_on = None

_MOVE_LIMITS_KEY = sa.text(
    """
    UPDATE app_settings
    SET config = jsonb_set(
        config #- CAST(:old_path AS text[]),
        CAST(:new_path AS text[]),
        config -> 'limits' -> :old
    )
    WHERE jsonb_exists(config -> 'limits', :old)
    """
)


def _move_limits_key(old: str, new: str) -> None:
    op.execute(
        _MOVE_LIMITS_KEY.bindparams(
            old=old, old_path=["limits", old], new_path=["limits", new]
        )
    )


def upgrade() -> None:
    _move_limits_key("announcement_timeout", "announcement_cooldown_seconds")


def downgrade() -> None:
    _move_limits_key("announcement_cooldown_seconds", "announcement_timeout")
