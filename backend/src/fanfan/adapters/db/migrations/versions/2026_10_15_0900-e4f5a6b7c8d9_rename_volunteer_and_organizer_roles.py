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

# revision identifiers, used by Alembic.
revision = "e4f5a6b7c8d9"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None

# (table, check constraint name). Both columns are named ``role``.
_ROLE_COLUMNS = (("users", "ck_users_userrole"), ("tickets", "ck_tickets_userrole"))

_RENAMES = [("helper", "volunteer"), ("org", "organizer")]

_OLD_VALUES = ["visitor", "participant", "helper", "org"]
_NEW_VALUES = ["visitor", "participant", "volunteer", "organizer"]


def _rewrite(renames: list[tuple[str, str]], allowed: list[str]) -> None:
    conn = op.get_bind()
    for table, ck_name in _ROLE_COLUMNS:
        # Drop the CHECK first, otherwise the rewrite would violate it mid-flight.
        op.drop_constraint(op.f(ck_name), table, type_="check")
        for src, dst in renames:
            # table is a trusted literal from _ROLE_COLUMNS (never user input);
            # the values are passed as bound parameters.
            conn.execute(
                sa.text(f"UPDATE {table} SET role = :dst WHERE role = :src"),  # noqa: S608
                {"src": src, "dst": dst},
            )
        op.create_check_constraint(op.f(ck_name), table, sa.column("role").in_(allowed))

    for src, dst in renames:
        # Swap one element inside each JSONB array, keeping element order.
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
                WHERE roles ? :src
                """
            ),
            {"src": src, "dst": dst},
        )


def upgrade() -> None:
    _rewrite(_RENAMES, _NEW_VALUES)


def downgrade() -> None:
    _rewrite([(dst, src) for src, dst in _RENAMES], _OLD_VALUES)
