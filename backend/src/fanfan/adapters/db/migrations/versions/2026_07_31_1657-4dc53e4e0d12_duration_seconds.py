"""duration_seconds

Revision ID: 4dc53e4e0d12
Revises: b4d81f2ac907
Create Date: 2026-07-31 16:57:59.943711

Rename ``schedule_events.duration`` to ``duration_seconds`` and convert the
stored values from minutes to seconds.

The column always *meant* seconds — the timing service adds it to
``transition_buffer`` inside ``timedelta(seconds=...)`` — but the only writer is
the spreadsheet import, and the template and the on-screen column guide both
asked the organizer for whole minutes, which the parser stored unconverted. So
every existing row holds a minute count in a seconds field, and the projected
``≈ HH:MM`` on the schedule screen was ~60x short.

The conversion below therefore assumes every stored value is a minute count,
which is what the documented import contract produced. Autogenerate emitted this
as drop + create (it diffs schemas, not intent); rewritten as an ``alter_column``
rename so the data survives to be converted.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "4dc53e4e0d12"
down_revision = "b4d81f2ac907"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "schedule_events",
        "duration",
        new_column_name="duration_seconds",
    )
    op.execute(
        """
        UPDATE schedule_events
        SET duration_seconds = duration_seconds * 60
        """
    )


def downgrade() -> None:
    # Integer division, so a duration that is not a whole number of minutes
    # cannot round-trip — a 30-second act comes back as 0. That is inherent to
    # the column this reverts to, which had no way to express it.
    op.execute(
        """
        UPDATE schedule_events
        SET duration_seconds = duration_seconds / 60
        """
    )
    op.alter_column(
        "schedule_events",
        "duration_seconds",
        new_column_name="duration",
    )
