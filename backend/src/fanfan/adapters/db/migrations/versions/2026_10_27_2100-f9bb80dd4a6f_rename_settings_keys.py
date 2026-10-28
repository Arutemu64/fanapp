"""rename settings keys to say their unit or kind

limits.announcement_timeout -> announcement_cooldown_seconds, and the
festival/voting bounds take the `_at` suffix of a timestamp. The settings row
is one JSONB document, so each rename is a key move inside it.

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

# (old path, new path) inside app_settings.config
RENAMES = [
    (["limits", "announcement_timeout"], ["limits", "announcement_cooldown_seconds"]),
    (["festival_start"], ["festival_starts_at"]),
    (["festival_end"], ["festival_ends_at"]),
    (["voting_start"], ["voting_starts_at"]),
    (["voting_end"], ["voting_ends_at"]),
]

_MOVE_KEY = sa.text(
    """
    UPDATE app_settings
    SET config = jsonb_set(
        config #- CAST(:old_path AS text[]),
        CAST(:new_path AS text[]),
        config #> CAST(:old_path AS text[])
    )
    WHERE config #> CAST(:old_path AS text[]) IS NOT NULL
    """
)


def _move_key(old_path: list[str], new_path: list[str]) -> None:
    op.execute(_MOVE_KEY.bindparams(old_path=old_path, new_path=new_path))


def upgrade() -> None:
    for old_path, new_path in RENAMES:
        _move_key(old_path, new_path)


def downgrade() -> None:
    for old_path, new_path in RENAMES:
        _move_key(new_path, old_path)
