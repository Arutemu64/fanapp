"""rename volunteer and organizer roles

Renames two stored ``UserRole`` values so they match the domain language:
``helper`` → ``volunteer`` and ``org`` → ``organizer``. The role columns are
VARCHARs guarded by a CHECK constraint (``native_enum=False``), so this is a
hand-written constraint swap around a data rewrite; autogenerate sees nothing.

Existing rows are rewritten in ``users.role``, ``tickets.role`` and the
``mailings.roles`` JSONB arrays (the roles a broadcast targeted). Unpublished
outbox payloads are left alone: ``UserRole`` still accepts the old values on
read, which also covers in-flight NATS messages and clients on the old bundle.

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-10-15 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "e4f5a6b7c8d9"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None

_ROLE_COLUMNS = (("users", "ck_users_userrole"), ("tickets", "ck_tickets_userrole"))

_RENAMES = [("helper", "volunteer"), ("org", "organizer")]

_OLD_VALUES = ["visitor", "participant", "helper", "org"]
_NEW_VALUES = ["visitor", "participant", "volunteer", "organizer"]


def _rewrite(renames: list[tuple[str, str]], allowed: list[str]) -> None:
    conn = op.get_bind()
    op.execute("SET LOCAL lock_timeout = '5s'")
    for table, ck_name in _ROLE_COLUMNS:
        op.drop_constraint(op.f(ck_name), table, type_="check")
        role_table = sa.table(table, sa.column("role"))
        for src, dst in renames:
            conn.execute(
                sa.update(role_table).where(role_table.c.role == src).values(role=dst)
            )
        op.create_check_constraint(op.f(ck_name), table, sa.column("role").in_(allowed))

    for src, dst in renames:
        conn.execute(
            sa.text(
                """
                UPDATE mailings
                SET roles = (
                    SELECT jsonb_agg(
                        CASE WHEN elem = :src THEN :dst ELSE elem END
                        ORDER BY ord
                    )
                    FROM jsonb_array_elements_text(roles) WITH ORDINALITY AS t(elem, ord)
                )
                WHERE jsonb_typeof(roles) = 'array' AND roles ? :src
                """
            ),
            {"src": src, "dst": dst},
        )


def upgrade() -> None:
    _rewrite(_RENAMES, _NEW_VALUES)


def downgrade() -> None:
    _rewrite([(dst, src) for src, dst in _RENAMES], _OLD_VALUES)
