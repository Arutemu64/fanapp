"""limits_seconds_suffix

Revision ID: e0ed6c8fea0b
Revises: 4dc53e4e0d12
Create Date: 2026-07-31 17:00:52.650247

Rename the ``LimitsConfig`` keys inside ``app_settings.config`` to carry their
unit: ``announcement_timeout`` -> ``announcement_timeout_seconds`` and
``transition_buffer`` -> ``transition_buffer_seconds``.

Autogenerate cannot see this: the settings aggregate is stored as one JSONB
document (``AppSettingsMapper`` dumps the dataclass through adaptix), so a field
rename is a data change, not a schema change. Without it the old keys survive,
adaptix falls back to the dataclass defaults, and an operator's tuned values are
silently reset.

``jsonb_strip_nulls`` covers the row seeded by b0fbcd2bb975, whose ``limits``
holds only ``announcement_timeout``: reading the absent key yields JSON null,
and writing that null back would shadow the dataclass default with a value
adaptix cannot load as an int.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e0ed6c8fea0b"
down_revision = "4dc53e4e0d12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE app_settings
        SET config = jsonb_set(
            config,
            '{limits}',
            ((config -> 'limits') - 'announcement_timeout' - 'transition_buffer')
            || jsonb_strip_nulls(jsonb_build_object(
                'announcement_timeout_seconds',
                config -> 'limits' -> 'announcement_timeout',
                'transition_buffer_seconds',
                config -> 'limits' -> 'transition_buffer'
            ))
        )
        WHERE config -> 'limits' IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE app_settings
        SET config = jsonb_set(
            config,
            '{limits}',
            ((config -> 'limits')
                - 'announcement_timeout_seconds'
                - 'transition_buffer_seconds')
            || jsonb_strip_nulls(jsonb_build_object(
                'announcement_timeout',
                config -> 'limits' -> 'announcement_timeout_seconds',
                'transition_buffer',
                config -> 'limits' -> 'transition_buffer_seconds'
            ))
        )
        WHERE config -> 'limits' IS NOT NULL
        """
    )
