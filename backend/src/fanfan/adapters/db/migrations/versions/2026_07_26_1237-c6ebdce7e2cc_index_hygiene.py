"""index hygiene: drop three indexes no query used, add two the purges needed

Four index changes, all found by reviewing the models against the queries that
actually run (EXPLAIN against a seeded database, not inspection):

* ``ix_notifications_created_at`` / ``ix_outbox_events_published_at`` (added) —
  both retention sweeps (``delete_created_before``, ``delete_published_before``)
  filter on a bare timestamp range that no existing index could answer:
  notifications' composite index leads with ``user_id``, and the outbox partial
  index covers the exact complement (``published_at IS NULL``). Each sweep
  therefore full-scanned its table on *every* cron tick — including in the
  steady state, where the previous tick already deleted everything eligible and
  the scan returns zero rows.
* ``ix_users_role`` (added) — the broadcast fan-out (``read_all_by_roles``)
  targets org/helper users, a tiny slice of a table dominated by visitors.
* ``ix_users_receive_all_announcements`` (dropped) — a partial index on the same
  column as its own predicate, so the indexed value was constant and carried no
  information. The column also defaults to true, meaning the predicate matched
  ~every row: the planner seq-scanned past it regardless. Write overhead only.
* ``ix_participants_title`` / ``ix_schedule_events_title`` (dropped) — no query
  in the backend filters or sorts on either column. The tables are small, so the
  cost was never the point: an index implies a supported lookup that did not
  exist.

Index operations run ``CONCURRENTLY`` inside an autocommit block so they never
block writes on the previous release's containers, which keep serving traffic
while ``just deploy`` runs this migration (the app services gate on the
migration only for their *own* start). ``notifications`` is the table that makes
this matter — it is the one here that grows without bound.

The trade-off of ``CONCURRENTLY``: this migration is not atomic. If a build is
interrupted, Postgres leaves an INVALID index behind; drop it by hand and re-run
rather than assuming the revision half-applied.

Revision ID: c6ebdce7e2cc
Revises: 1a3c5e7d9b02
Create Date: 2026-07-26 12:37:15.576940

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c6ebdce7e2cc"
down_revision = "1a3c5e7d9b02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_notifications_created_at",
            "notifications",
            ["created_at"],
            unique=False,
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_outbox_events_published_at",
            "outbox_events",
            ["published_at"],
            unique=False,
            postgresql_concurrently=True,
        )
        op.create_index(
            op.f("ix_users_role"),
            "users",
            ["role"],
            unique=False,
            postgresql_concurrently=True,
        )

        op.drop_index(
            op.f("ix_participants_title"),
            table_name="participants",
            postgresql_concurrently=True,
        )
        op.drop_index(
            op.f("ix_schedule_events_title"),
            table_name="schedule_events",
            postgresql_concurrently=True,
        )
        op.drop_index(
            op.f("ix_users_receive_all_announcements"),
            table_name="users",
            postgresql_where="receive_all_announcements",
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(
            op.f("ix_users_receive_all_announcements"),
            "users",
            ["receive_all_announcements"],
            unique=False,
            postgresql_where="receive_all_announcements",
            postgresql_concurrently=True,
        )
        op.create_index(
            op.f("ix_schedule_events_title"),
            "schedule_events",
            ["title"],
            unique=False,
            postgresql_concurrently=True,
        )
        op.create_index(
            op.f("ix_participants_title"),
            "participants",
            ["title"],
            unique=False,
            postgresql_concurrently=True,
        )

        op.drop_index(
            op.f("ix_users_role"),
            table_name="users",
            postgresql_concurrently=True,
        )
        op.drop_index(
            "ix_outbox_events_published_at",
            table_name="outbox_events",
            postgresql_concurrently=True,
        )
        op.drop_index(
            "ix_notifications_created_at",
            table_name="notifications",
            postgresql_concurrently=True,
        )
