from uuid import UUID, uuid7

from sqlalchemy import Uuid, func, select
from sqlalchemy.orm import (
    Mapped,
    column_property,
    declared_attr,
    mapped_column,
    relationship,
)

from fanfan.adapters.db.models.base import BaseORM
from fanfan.adapters.db.models.participant import ParticipantORM


class NominationORM(BaseORM):
    __tablename__ = "nominations"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    cosplay2_id: Mapped[int] = mapped_column(unique=True, index=True)
    code: Mapped[str] = mapped_column(unique=True)
    title: Mapped[str] = mapped_column(unique=True)
    is_votable: Mapped[bool] = mapped_column(server_default="False")

    participants: Mapped[list[ParticipantORM]] = relationship(
        back_populates="nomination"
    )

    @declared_attr
    @classmethod
    def participants_count(cls):
        return column_property(
            select(func.count(ParticipantORM.id))
            .where(ParticipantORM.nomination_id == cls.id)
            .correlate_except(ParticipantORM)
            .scalar_subquery(),
            deferred=True,
        )

    def __str__(self) -> str:
        return self.title
