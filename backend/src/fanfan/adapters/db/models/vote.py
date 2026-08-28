from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import BaseORM
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from fanfan.adapters.db.models.nomination import NominationORM
    from fanfan.adapters.db.models.participant import ParticipantORM


class VoteORM(UUIDPrimaryKeyMixin, BaseORM):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("user_id", "participant_id"),)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    participant_id: Mapped[UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), index=True
    )

    participant: Mapped[ParticipantORM] = relationship()
    nomination: Mapped[NominationORM] = relationship(
        secondary="participants",
        viewonly=True,
    )
