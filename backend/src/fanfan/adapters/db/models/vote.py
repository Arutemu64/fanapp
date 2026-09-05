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
    __table_args__ = (
        UniqueConstraint("user_id", "participant_id"),
        # One vote per nomination per user, enforced in the DB: the app-level
        # check in AddVote can race (its FOR UPDATE locks nothing when no vote
        # exists yet), so this constraint is the real backstop against a
        # concurrent double-vote across two participants in the same nomination.
        UniqueConstraint("user_id", "nomination_id", name="uq_votes_user_nomination"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    participant_id: Mapped[UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), index=True
    )
    # Denormalised from the participant so a unique constraint can enforce the
    # per-nomination rule (a constraint cannot span the participants join).
    nomination_id: Mapped[UUID] = mapped_column(
        ForeignKey("nominations.id", ondelete="CASCADE"), index=True
    )

    participant: Mapped[ParticipantORM] = relationship()
    nomination: Mapped[NominationORM] = relationship()
