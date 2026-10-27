"""add quest

Adds the quest points ledger (``quest_awards``, docs/adr/0035), the
``quest:award`` and ``quest:manage`` permissions, and renames the
``points_received`` notification type to ``quest``, since quest notifications
also announce cancelled awards.

The new table starts empty. Widening the permission CHECK touches no row. No
code ever sent a ``points_received`` notification, so the deployed data should
hold none; the UPDATE still rewrites any that exist, between dropping the old
CHECK and creating the new one so neither rejects a row mid-flight. Both enum
swaps are hand-written: autogenerate does not diff CHECK bodies.

Revision ID: fd9f2839bb05
Revises: e4f5a6b7c8d9
Create Date: 2026-10-16 16:09:21.413091

"""

import sqlalchemy as sa
from alembic import op

_PERMISSION_CK = "ck_user_permissions_permissionname"
_PERMISSIONS_EXISTING = [
    "*",
    "schedule:manage",
    "schedule:import",
    "notifications:send",
    "settings:manage",
    "tickets:generate",
    "sync:run",
    "demo:seed",
    "feedback:read",
    "voting:manage",
    "users:read",
    "users:manage",
]
_PERMISSIONS_NEW = ["quest:award", "quest:manage"]

_NOTIFICATION_TYPE_CK = "ck_notifications_notificationtype"
_NOTIFICATION_TYPES_KEPT = [
    "default",
    "schedule_change",
    "schedule_subscription",
    "message",
    "broadcast",
    "test",
]
_OLD_TYPE = "points_received"
_NEW_TYPE = "quest"

revision = "fd9f2839bb05"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quest_awards",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("awarded_by", sa.Uuid(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name=op.f("ck_quest_awards_amount_positive")),
        sa.ForeignKeyConstraint(
            ["awarded_by"],
            ["users.id"],
            name=op.f("fk_quest_awards_awarded_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["cancelled_by"],
            ["users.id"],
            name=op.f("fk_quest_awards_cancelled_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_quest_awards_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quest_awards")),
    )
    op.create_index(
        op.f("ix_quest_awards_awarded_by"), "quest_awards", ["awarded_by"], unique=False
    )
    op.create_index(
        "ix_quest_awards_user_id_active",
        "quest_awards",
        ["user_id"],
        unique=False,
        postgresql_where=sa.text("cancelled_at IS NULL"),
    )

    op.drop_constraint(op.f(_PERMISSION_CK), "user_permissions", type_="check")
    op.create_check_constraint(
        op.f(_PERMISSION_CK),
        "user_permissions",
        sa.column("permission").in_([*_PERMISSIONS_EXISTING, *_PERMISSIONS_NEW]),
    )

    _swap_notification_type(_OLD_TYPE, _NEW_TYPE)


def downgrade() -> None:
    _swap_notification_type(_NEW_TYPE, _OLD_TYPE)

    permissions = sa.table("user_permissions", sa.column("permission"))
    op.execute(
        permissions.delete().where(permissions.c.permission.in_(_PERMISSIONS_NEW))
    )
    op.drop_constraint(op.f(_PERMISSION_CK), "user_permissions", type_="check")
    op.create_check_constraint(
        op.f(_PERMISSION_CK),
        "user_permissions",
        sa.column("permission").in_(_PERMISSIONS_EXISTING),
    )

    op.drop_index(
        "ix_quest_awards_user_id_active",
        table_name="quest_awards",
        postgresql_where=sa.text("cancelled_at IS NULL"),
    )
    op.drop_index(op.f("ix_quest_awards_awarded_by"), table_name="quest_awards")
    op.drop_table("quest_awards")


def _swap_notification_type(old: str, new: str) -> None:
    op.drop_constraint(op.f(_NOTIFICATION_TYPE_CK), "notifications", type_="check")
    notifications = sa.table("notifications", sa.column("type"))
    op.execute(
        notifications.update().where(notifications.c.type == old).values(type=new)
    )
    op.create_check_constraint(
        op.f(_NOTIFICATION_TYPE_CK),
        "notifications",
        sa.column("type").in_([*_NOTIFICATION_TYPES_KEPT, new]),
    )
