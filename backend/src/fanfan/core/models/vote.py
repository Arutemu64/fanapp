from dataclasses import dataclass
from typing import Self

from fanfan.core.events.voting import VoteCreated, VoteDeleted
from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.participant import ParticipantId
from fanfan.core.vo.user import UserId
from fanfan.core.vo.vote import VoteId, generate_vote_id


@dataclass(slots=True, kw_only=True)
class Vote(AggregateRoot):
    id: VoteId
    user_id: UserId
    participant_id: ParticipantId

    @classmethod
    def create(cls, *, user_id: UserId, participant_id: ParticipantId) -> Self:
        vote = cls(
            id=generate_vote_id(), user_id=user_id, participant_id=participant_id
        )
        vote.record_event(
            VoteCreated(
                vote_id=vote.id,
                user_id=vote.user_id,
                participant_id=vote.participant_id,
            )
        )
        return vote

    def delete(self) -> None:
        self.record_event(
            VoteDeleted(
                vote_id=self.id,
                user_id=self.user_id,
                participant_id=self.participant_id,
            )
        )
