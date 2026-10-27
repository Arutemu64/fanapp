"""schema_hardening_fixes

Revision ID: c9d4e1f83a27
Revises: b7c3e9d24a10
Create Date: 2026-07-14 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "c9d4e1f83a27"
down_revision = "b7c3e9d24a10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.create_index(
        "ix_users_username_lower",
        "users",
        [sa.text("lower(username)")],
        unique=True,
    )

    op.drop_constraint(
        op.f("fk_tickets_used_by_user_id_users"), "tickets", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("fk_tickets_used_by_user_id_users"),
        "tickets",
        "users",
        ["used_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_constraint(
        op.f("fk_notifications_mailing_id_mailings"),
        "notifications",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_notifications_mailing_id_mailings"),
        "notifications",
        "mailings",
        ["mailing_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_check_constraint(
        op.f("ck_app_settings_single_row"),
        "app_settings",
        "id = 1",
    )

    op.create_unique_constraint(
        op.f("uq_social_identities_user_id"),
        "social_identities",
        ["user_id", "provider"],
    )
    op.drop_index(op.f("ix_social_identities_user_id"), table_name="social_identities")

    op.drop_index(
        op.f("ix_participant_values_participant_id"), table_name="participant_values"
    )
    op.drop_table("participant_values")


def downgrade() -> None:
    op.create_table(
        "participant_values",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "TEXT",
                "PHONE",
                "TEXTAREA",
                "LINK",
                "CHECKBOX",
                "USER",
                "DURATION",
                "IMAGE",
                "SELECT",
                "NUM",
                "FILE",
                name="valuetype",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("value", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["participant_id"],
            ["participants.id"],
            name=op.f("fk_participant_values_participant_id_participants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_participant_values")),
    )
    op.create_index(
        op.f("ix_participant_values_participant_id"),
        "participant_values",
        ["participant_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_social_identities_user_id"),
        "social_identities",
        ["user_id"],
        unique=False,
    )
    op.drop_constraint(
        op.f("uq_social_identities_user_id"), "social_identities", type_="unique"
    )

    op.drop_constraint(
        op.f("ck_app_settings_single_row"), "app_settings", type_="check"
    )

    op.drop_constraint(
        op.f("fk_notifications_mailing_id_mailings"),
        "notifications",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_notifications_mailing_id_mailings"),
        "notifications",
        "mailings",
        ["mailing_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        op.f("fk_tickets_used_by_user_id_users"), "tickets", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("fk_tickets_used_by_user_id_users"),
        "tickets",
        "users",
        ["used_by_user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_index("ix_users_username_lower", table_name="users")
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
