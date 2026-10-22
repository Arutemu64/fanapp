"""move TicketsCloud event roles from env to app settings

The event-to-role mapping left the ``TCLOUD__EVENT_IDS_MAP`` env var for
``app_settings.config -> tickets -> tcloud_event_roles``, which organizers edit
from the tickets tool. ``AppSettings`` loads a missing ``tickets`` key as an
empty mapping, so no row needs rewriting for the app to boot.

The backfill copies the env var once, if the migration runs with it set (the
compose ``migration`` service reads the same ``.env``). Without it, every
TicketsCloud ticket imported after the deploy would silently grant the visitor
role until someone re-entered the mapping. A row that already holds a
``tickets`` key is left alone, so a re-run never overwrites the organizers' edit.

Revision ID: 7c1e5a9b3d20
Revises: 3fd0d71c9a0f
Create Date: 2026-10-22 12:00:00.000000

"""

import json
import logging
import os

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7c1e5a9b3d20"
down_revision = "3fd0d71c9a0f"
branch_labels = None
depends_on = None

logger = logging.getLogger(f"alembic.runtime.migration.{revision}")

_ENV_VAR = "TCLOUD__EVENT_IDS_MAP"
# UserRole values, frozen here: a migration must not track the live enum.
_ROLES = {"visitor", "participant", "volunteer", "organizer"}


def _event_roles_from_env() -> dict[str, str]:
    raw = os.environ.get(_ENV_VAR)
    if not raw:
        return {}
    parsed = json.loads(raw)
    event_roles: dict[str, str] = {}
    for event_id, role in parsed.items():
        if role not in _ROLES:
            # Fail loudly: the old config refused to boot on a bad role too, so
            # this value never worked, and dropping it quietly would hide that.
            msg = f"{_ENV_VAR}: unknown role {role!r} for event {event_id!r}"
            raise ValueError(msg)
        event_roles[str(event_id).strip()] = role
    return event_roles


def upgrade() -> None:
    event_roles = _event_roles_from_env()
    if not event_roles:
        return
    op.get_bind().execute(
        sa.text(
            "UPDATE app_settings "
            "SET config = config || jsonb_build_object("
            "'tickets', jsonb_build_object("
            "'tcloud_event_roles', CAST(:event_roles AS jsonb))) "
            "WHERE config -> 'tickets' IS NULL"
        ),
        {"event_roles": json.dumps(event_roles)},
    )
    logger.info(
        "Copied %d TicketsCloud event roles from %s", len(event_roles), _ENV_VAR
    )


def downgrade() -> None:
    # The older code reads the mapping from the env var again; the key would
    # only be a stale copy it never looks at.
    op.execute("UPDATE app_settings SET config = config - 'tickets'")
