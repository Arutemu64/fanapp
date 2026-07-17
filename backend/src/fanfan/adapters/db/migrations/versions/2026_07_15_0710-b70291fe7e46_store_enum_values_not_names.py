"""store enum values not names

Revision ID: b70291fe7e46
Revises: 344a57c66154
Create Date: 2026-07-15 07:10:00.000000

Switch the remaining ``native_enum=False`` StrEnum columns from storing the
member *name* (e.g. "VISITOR") to storing the member *value* (e.g. "visitor"),
matching what the domain, API, DTOs and frontend already use. Rewrites the
stored data, swaps the CHECK constraint value list, and updates the two
``role`` server defaults. ``Permission`` and ``UserFlagName`` already stored
values, so they are untouched.

The name→value maps are pinned as literals so this migration stays fixed to the
schema at this revision and does not drift if an enum gains members later.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b70291fe7e46"
down_revision = "344a57c66154"
branch_labels = None
depends_on = None


# (table, column, check constraint name, [(member_name, member_value), ...]).
# The pairs double as the name→value rewrite map and the new/old CHECK value
# lists (new = values, old = names).
_ENUM_COLUMNS = (
    (
        "users",
        "role",
        "ck_users_userrole",
        [
            ("VISITOR", "visitor"),
            ("PARTICIPANT", "participant"),
            ("HELPER", "helper"),
            ("ORG", "org"),
        ],
    ),
    (
        "tickets",
        "role",
        "ck_tickets_userrole",
        [
            ("VISITOR", "visitor"),
            ("PARTICIPANT", "participant"),
            ("HELPER", "helper"),
            ("ORG", "org"),
        ],
    ),
    (
        "notifications",
        "type",
        "ck_notifications_notificationtype",
        [
            ("DEFAULT", "default"),
            ("SCHEDULE_CHANGE", "schedule_change"),
            ("SCHEDULE_SUBSCRIPTION", "schedule_subscription"),
            ("MESSAGE", "message"),
            ("POINTS_RECEIVED", "points_received"),
            ("BROADCAST", "broadcast"),
            ("TEST", "test"),
        ],
    ),
    (
        "mailings",
        "status",
        "ck_mailings_mailingstatus",
        [
            ("PENDING", "pending"),
            ("SENDING", "sending"),
            ("FINISHED", "finished"),
            ("CANCELLED", "cancelled"),
            ("FAILED", "failed"),
        ],
    ),
    (
        "schedule_changes",
        "type",
        "ck_schedule_changes_schedulechangetype",
        [
            ("SET_AS_CURRENT", "set_as_current"),
            ("MOVED", "moved"),
            ("SKIPPED", "skipped"),
            ("UNSKIPPED", "unskipped"),
        ],
    ),
)

# Columns whose server_default holds a role and must move name↔value with the data.
_ROLE_DEFAULT_COLUMNS = (("users", "role"), ("tickets", "role"))


def _rewrite(table: str, column: str, mapping: list[tuple[str, str]]) -> None:
    conn = op.get_bind()
    for src, dst in mapping:
        # table/column are trusted literals from _ENUM_COLUMNS (never user
        # input); the migrated values are passed as bound parameters.
        conn.execute(
            sa.text(f"UPDATE {table} SET {column} = :dst WHERE {column} = :src"),  # noqa: S608
            {"src": src, "dst": dst},
        )


def upgrade() -> None:
    for table, column, ck_name, pairs in _ENUM_COLUMNS:
        # Drop the name-based CHECK first, otherwise the value rewrite would
        # violate it mid-flight.
        op.drop_constraint(op.f(ck_name), table, type_="check")
        _rewrite(table, column, pairs)
        op.create_check_constraint(
            op.f(ck_name),
            table,
            sa.column(column).in_([value for _, value in pairs]),
        )
    for table, column in _ROLE_DEFAULT_COLUMNS:
        op.alter_column(table, column, server_default="visitor")


def downgrade() -> None:
    for table, column in _ROLE_DEFAULT_COLUMNS:
        op.alter_column(table, column, server_default="VISITOR")
    for table, column, ck_name, pairs in _ENUM_COLUMNS:
        op.drop_constraint(op.f(ck_name), table, type_="check")
        # Reverse the map: value → name.
        _rewrite(table, column, [(value, name) for name, value in pairs])
        op.create_check_constraint(
            op.f(ck_name),
            table,
            sa.column(column).in_([name for name, _ in pairs]),
        )
