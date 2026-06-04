from typing import ClassVar

from fanfan.core.events.base import AppEvent
from fanfan.core.vo.participant import ParticipantId
from fanfan.core.vo.user import UserId
from fanfan.core.vo.vote import VoteId


class VoteCreated(AppEvent):
    subject: ClassVar[str] = "votes.created"

    vote_id: VoteId
    user_id: UserId
    participant_id: ParticipantId


class VoteDeleted(AppEvent):
    subject: ClassVar[str] = "votes.deleted"

    vote_id: VoteId
    user_id: UserId
    participant_id: ParticipantId
