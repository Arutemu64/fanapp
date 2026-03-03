from __future__ import annotations

from uuid import uuid7

from sqlalchemy import Uuid, func, select
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from fanfan.adapters.db.models.base import BaseORM
from fanfan.adapters.db.models.participant import ParticipantORM
from fanfan.core.vo.nomination import NominationCode, NominationId


class NominationORM(BaseORM):
    __tablename__ = "nominations"

    id: Mapped[NominationId] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid7
    )
    cosplay2_id: Mapped[int] = mapped_column(unique=True, index=True)
    code: Mapped[NominationCode] = mapped_column(unique=True)
    title: Mapped[str] = mapped_column(unique=True)
    is_votable: Mapped[bool] = mapped_column(server_default="False")

    participants: Mapped[list[ParticipantORM]] = relationship(
        back_populates="nomination"
    )

    participants_count = column_property(
        select(func.count(ParticipantORM.id))
        .where(ParticipantORM.nomination_id == id)  # noqa: A003
        .correlate_except(ParticipantORM)
        .scalar_subquery(),
        deferred=True,
    )

    def __str__(self) -> str:
        return self.title
