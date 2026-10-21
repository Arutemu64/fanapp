"""add_procrastinate_schema

Creates the tables, types, functions and triggers of the Procrastinate job
queue (ADR-0041), from the schema SQL shipped with procrastinate 3.10.0 and
vendored under ``migrations/sql/``. Procrastinate tracks no applied version of
its own and leaves upgrades to the app
(https://procrastinate.readthedocs.io/en/stable/howto/production/migrations.html),
so a later procrastinate release that changes the schema gets its own Alembic
revision running that release's migration scripts, vendored the same way.

Revision ID: e9c2a8d22f17
Revises: c3d9e1f2a4b6
Create Date: 2026-10-21 13:00:00.000000

"""

from pathlib import Path

from alembic import op

# revision identifiers, used by Alembic.
revision = "e9c2a8d22f17"
down_revision = "c3d9e1f2a4b6"
branch_labels = None
depends_on = None

# Vendored, not read from the installed package: a migration must not change
# when the code it was written against does.
_SCHEMA_SQL = Path(__file__).parent.parent / "sql" / "procrastinate-3.10.0-schema.sql"

_TABLES = (
    "procrastinate_events",
    "procrastinate_periodic_defers",
    "procrastinate_jobs",
    "procrastinate_workers",
)
# Functions that take or return a table's row type, dropped before the tables.
_FUNCTIONS = (
    "procrastinate_cancel_job_v1",
    "procrastinate_defer_jobs_v1",
    "procrastinate_defer_periodic_job_v2",
    "procrastinate_fetch_job_v2",
    "procrastinate_finish_job_v1",
    "procrastinate_prune_stalled_workers_v1",
    "procrastinate_register_worker_v1",
    "procrastinate_retry_job_v1",
    "procrastinate_retry_job_v2",
    "procrastinate_unregister_worker_v1",
    "procrastinate_update_heartbeat_v1",
)
# Functions the tables' triggers call, dropped after the tables (and so their
# triggers) are gone.
_TRIGGER_FUNCTIONS = (
    "procrastinate_notify_queue_abort_job_v1",
    "procrastinate_notify_queue_job_inserted_v1",
    "procrastinate_trigger_abort_requested_events_procedure_v1",
    "procrastinate_trigger_function_scheduled_events_v1",
    "procrastinate_trigger_function_status_events_insert_v1",
    "procrastinate_trigger_function_status_events_update_v1",
    "procrastinate_unlink_periodic_defers_v1",
)
_TYPES = (
    "procrastinate_job_to_defer_v1",
    "procrastinate_job_event_type",
    "procrastinate_job_status",
)


def upgrade() -> None:
    # Straight to the DBAPI cursor with no parameters at all: psycopg then
    # neither parses the script's `%` for placeholders nor refuses its several
    # statements, which it does once any parameters (even empty ones, as
    # SQLAlchemy's execute paths pass) are given.
    cursor = op.get_bind().connection.cursor()
    try:
        cursor.execute(_SCHEMA_SQL.read_text(encoding="utf-8"))
    finally:
        cursor.close()


def downgrade() -> None:
    for function in _FUNCTIONS:
        op.execute(f"DROP FUNCTION IF EXISTS {function}")
    for table in _TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table}")
    for function in _TRIGGER_FUNCTIONS:
        op.execute(f"DROP FUNCTION IF EXISTS {function}")
    for type_ in _TYPES:
        op.execute(f"DROP TYPE IF EXISTS {type_}")
