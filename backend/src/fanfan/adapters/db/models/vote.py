from typing import TYPE_CHECKING
from uuid import UUID, uuid7

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import BaseORM

if TYPE_CHECKING:
    from fanfan.adapters.db.models.nomination import NominationORM
    from fanfan.adapters.db.models.participant import ParticipantORM
    from fanfan.adapters.db.models.user import UserORM


class VoteORM(BaseORM):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("user_id", "participant_id"),)

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    participant_id: Mapped[UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), index=True
    )

    user: Mapped[UserORM] = relationship()
    participant: Mapped[ParticipantORM] = relationship()
    nomination: Mapped[NominationORM] = relationship(
        secondary="participants",
        viewonly=True,
    )
