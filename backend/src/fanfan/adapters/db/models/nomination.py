from sqlalchemy import func, select, text
from sqlalchemy.orm import (
    Mapped,
    column_property,
    declared_attr,
    mapped_column,
)

from fanfan.adapters.db.models.base import BaseORM
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.adapters.db.models.mixins.timestamps import UpdatedAtMixin
from fanfan.adapters.db.models.participant import ParticipantORM


class NominationORM(UUIDPrimaryKeyMixin, UpdatedAtMixin, BaseORM):
    __tablename__ = "nominations"

    cosplay2_id: Mapped[int] = mapped_column(unique=True, index=True)
    code: Mapped[str] = mapped_column(unique=True)
    title: Mapped[str] = mapped_column(unique=True)
    is_votable: Mapped[bool] = mapped_column(server_default=text("false"))
    works_url: Mapped[str | None] = mapped_column()

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
