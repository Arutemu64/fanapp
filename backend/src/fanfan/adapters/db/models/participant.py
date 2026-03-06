from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid7

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid, func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from fanfan.adapters.db.models.base import UUID_ID_SERVER_DEFAULT, BaseORM
from fanfan.adapters.db.models.vote import VoteORM
from fanfan.core.vo.nomination import NominationId
from fanfan.core.vo.participant import ParticipantId, ValueType

if TYPE_CHECKING:
    from fanfan.adapters.db.models.nomination import NominationORM


class ParticipantORM(BaseORM):
    __tablename__ = "participants"
    __table_args__ = (UniqueConstraint("nomination_id", "voting_number"),)

    id: Mapped[ParticipantId] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    cosplay2_id: Mapped[int] = mapped_column(unique=True, index=True)
    title: Mapped[str] = mapped_column(index=True)
    voting_number: Mapped[int | None] = mapped_column()
    nomination_id: Mapped[NominationId] = mapped_column(
        ForeignKey("nominations.id", ondelete="CASCADE"),
    )

    values: Mapped[list[ParticipantValueORM]] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan",
    )
    nomination: Mapped[NominationORM] = relationship()
    votes_count = column_property(
        select(func.count(VoteORM.id))
        .where(VoteORM.participant_id == id)  # noqa: A003
        .correlate_except(VoteORM)
        .scalar_subquery(),
        deferred=True,
    )

    def __str__(self) -> str:
        return self.title


class ParticipantValueORM(BaseORM):
    __tablename__ = "participant_values"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    participant_id: Mapped[ParticipantId] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column()
    type: Mapped[ValueType] = mapped_column(postgresql.ENUM(ValueType))
    value: Mapped[str | None] = mapped_column()

    participant: Mapped[ParticipantORM] = relationship(back_populates="values")
