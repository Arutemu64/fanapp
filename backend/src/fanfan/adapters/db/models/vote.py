from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid7

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import UUID_ID_SERVER_DEFAULT, BaseORM
from fanfan.core.vo.participant import ParticipantId
from fanfan.core.vo.user import UserId
from fanfan.core.vo.vote import VoteId

if TYPE_CHECKING:
    from fanfan.adapters.db.models.nomination import NominationORM
    from fanfan.adapters.db.models.participant import ParticipantORM
    from fanfan.adapters.db.models.user import UserORM


class VoteORM(BaseORM):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("user_id", "participant_id"),)

    id: Mapped[VoteId] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    user_id: Mapped[UserId] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    participant_id: Mapped[ParticipantId] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE")
    )

    user: Mapped[UserORM] = relationship()
    participant: Mapped[ParticipantORM] = relationship()
    nomination: Mapped[NominationORM] = relationship(
        secondary="participants",
        viewonly=True,
    )
