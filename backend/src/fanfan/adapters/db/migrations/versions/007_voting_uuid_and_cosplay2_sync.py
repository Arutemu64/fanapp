"""voting uuid ids and cosplay2 sync fields

Revision ID: 007
Revises: 006
Create Date: 2026-03-03 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def _int_to_uuid_sql(column_name: str) -> str:
    return (
        "(" 
        f"substr(lpad(to_hex({column_name}), 32, '0'), 1, 8) || '-' || "
        f"substr(lpad(to_hex({column_name}), 32, '0'), 9, 4) || '-' || "
        f"substr(lpad(to_hex({column_name}), 32, '0'), 13, 4) || '-' || "
        f"substr(lpad(to_hex({column_name}), 32, '0'), 17, 4) || '-' || "
        f"substr(lpad(to_hex({column_name}), 32, '0'), 21, 12))::uuid"
    )


def upgrade() -> None:
    op.add_column("nominations", sa.Column("cosplay2_id", sa.Integer(), nullable=True))
    op.execute("UPDATE nominations SET cosplay2_id = id")
    op.alter_column("nominations", "cosplay2_id", nullable=False)
    op.create_index(op.f("ix_nominations_cosplay2_id"), "nominations", ["cosplay2_id"], unique=True)

    op.add_column("participants", sa.Column("cosplay2_id", sa.Integer(), nullable=True))
    op.execute("UPDATE participants SET cosplay2_id = id")
    op.alter_column("participants", "cosplay2_id", nullable=False)
    op.create_index(op.f("ix_participants_cosplay2_id"), "participants", ["cosplay2_id"], unique=True)

    op.drop_constraint(op.f("fk_participants_nomination_id_nominations"), "participants", type_="foreignkey")
    op.drop_constraint(op.f("fk_participant_values_participant_id_participants"), "participant_values", type_="foreignkey")
    op.drop_constraint(op.f("fk_votes_participant_id_participants"), "votes", type_="foreignkey")

    op.add_column("nominations", sa.Column("id_uuid", sa.Uuid(), nullable=True))
    op.add_column("participants", sa.Column("id_uuid", sa.Uuid(), nullable=True))
    op.add_column("participants", sa.Column("nomination_id_uuid", sa.Uuid(), nullable=True))
    op.add_column("participant_values", sa.Column("participant_id_uuid", sa.Uuid(), nullable=True))
    op.add_column("votes", sa.Column("participant_id_uuid", sa.Uuid(), nullable=True))

    op.execute(f"UPDATE nominations SET id_uuid = {_int_to_uuid_sql('id')}")
    op.execute(f"UPDATE participants SET id_uuid = {_int_to_uuid_sql('id')}")
    op.execute(
        """
        UPDATE participants p
        SET nomination_id_uuid = n.id_uuid
        FROM nominations n
        WHERE p.nomination_id = n.id
        """
    )
    op.execute(
        """
        UPDATE participant_values pv
        SET participant_id_uuid = p.id_uuid
        FROM participants p
        WHERE pv.participant_id = p.id
        """
    )
    op.execute(
        """
        UPDATE votes v
        SET participant_id_uuid = p.id_uuid
        FROM participants p
        WHERE v.participant_id = p.id
        """
    )

    op.drop_constraint(op.f("pk_nominations"), "nominations", type_="primary")
    op.drop_constraint(op.f("pk_participants"), "participants", type_="primary")

    op.drop_column("nominations", "id")
    op.drop_column("participants", "id")
    op.drop_column("participants", "nomination_id")
    op.drop_column("participant_values", "participant_id")
    op.drop_column("votes", "participant_id")

    op.alter_column("nominations", "id_uuid", new_column_name="id", nullable=False)
    op.alter_column("participants", "id_uuid", new_column_name="id", nullable=False)
    op.alter_column("participants", "nomination_id_uuid", new_column_name="nomination_id", nullable=False)
    op.alter_column("participant_values", "participant_id_uuid", new_column_name="participant_id", nullable=False)
    op.alter_column("votes", "participant_id_uuid", new_column_name="participant_id", nullable=False)

    op.create_primary_key(op.f("pk_nominations"), "nominations", ["id"])
    op.create_primary_key(op.f("pk_participants"), "participants", ["id"])

    op.create_foreign_key(
        op.f("fk_participants_nomination_id_nominations"),
        "participants",
        "nominations",
        ["nomination_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_participant_values_participant_id_participants"),
        "participant_values",
        "participants",
        ["participant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_votes_participant_id_participants"),
        "votes",
        "participants",
        ["participant_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_participants_nomination_id_nominations"), "participants", type_="foreignkey")
    op.drop_constraint(op.f("fk_participant_values_participant_id_participants"), "participant_values", type_="foreignkey")
    op.drop_constraint(op.f("fk_votes_participant_id_participants"), "votes", type_="foreignkey")

    op.add_column("nominations", sa.Column("id_int", sa.Integer(), nullable=True))
    op.add_column("participants", sa.Column("id_int", sa.Integer(), nullable=True))
    op.add_column("participants", sa.Column("nomination_id_int", sa.Integer(), nullable=True))
    op.add_column("participant_values", sa.Column("participant_id_int", sa.Integer(), nullable=True))
    op.add_column("votes", sa.Column("participant_id_int", sa.Integer(), nullable=True))

    op.execute("UPDATE nominations SET id_int = cosplay2_id")
    op.execute("UPDATE participants SET id_int = cosplay2_id")
    op.execute(
        """
        UPDATE participants p
        SET nomination_id_int = n.cosplay2_id
        FROM nominations n
        WHERE p.nomination_id = n.id
        """
    )
    op.execute(
        """
        UPDATE participant_values pv
        SET participant_id_int = p.cosplay2_id
        FROM participants p
        WHERE pv.participant_id = p.id
        """
    )
    op.execute(
        """
        UPDATE votes v
        SET participant_id_int = p.cosplay2_id
        FROM participants p
        WHERE v.participant_id = p.id
        """
    )

    op.drop_constraint(op.f("pk_nominations"), "nominations", type_="primary")
    op.drop_constraint(op.f("pk_participants"), "participants", type_="primary")

    op.drop_column("nominations", "id")
    op.drop_column("participants", "id")
    op.drop_column("participants", "nomination_id")
    op.drop_column("participant_values", "participant_id")
    op.drop_column("votes", "participant_id")

    op.alter_column("nominations", "id_int", new_column_name="id", nullable=False)
    op.alter_column("participants", "id_int", new_column_name="id", nullable=False)
    op.alter_column("participants", "nomination_id_int", new_column_name="nomination_id", nullable=False)
    op.alter_column("participant_values", "participant_id_int", new_column_name="participant_id", nullable=False)
    op.alter_column("votes", "participant_id_int", new_column_name="participant_id", nullable=False)

    op.create_primary_key(op.f("pk_nominations"), "nominations", ["id"])
    op.create_primary_key(op.f("pk_participants"), "participants", ["id"])

    op.create_foreign_key(
        op.f("fk_participants_nomination_id_nominations"),
        "participants",
        "nominations",
        ["nomination_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_participant_values_participant_id_participants"),
        "participant_values",
        "participants",
        ["participant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_votes_participant_id_participants"),
        "votes",
        "participants",
        ["participant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_index(op.f("ix_participants_cosplay2_id"), table_name="participants")
    op.drop_index(op.f("ix_nominations_cosplay2_id"), table_name="nominations")
    op.drop_column("participants", "cosplay2_id")
    op.drop_column("nominations", "cosplay2_id")
