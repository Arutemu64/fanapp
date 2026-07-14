from typing import TYPE_CHECKING
from uuid import UUID, uuid7

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid, func, select
from sqlalchemy.orm import (
    Mapped,
    column_property,
    declared_attr,
    mapped_column,
    relationship,
)

from fanfan.adapters.db.models.base import BaseORM
from fanfan.adapters.db.models.vote import VoteORM

if TYPE_CHECKING:
    from fanfan.adapters.db.models.nomination import NominationORM


class ParticipantORM(BaseORM):
    __tablename__ = "participants"
    __table_args__ = (UniqueConstraint("nomination_id", "voting_number"),)

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    cosplay2_id: Mapped[int] = mapped_column(unique=True, index=True)
    title: Mapped[str] = mapped_column(index=True)
    voting_number: Mapped[int | None] = mapped_column()
    nomination_id: Mapped[UUID] = mapped_column(
        ForeignKey("nominations.id", ondelete="CASCADE"),
    )

    nomination: Mapped[NominationORM] = relationship()

    @declared_attr
    @classmethod
    def votes_count(cls):
        return column_property(
            select(func.count(VoteORM.id))
            .where(VoteORM.participant_id == cls.id)
            .correlate_except(VoteORM)
            .scalar_subquery(),
            deferred=True,
        )

    def __str__(self) -> str:
        return self.title
