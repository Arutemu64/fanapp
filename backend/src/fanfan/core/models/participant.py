from dataclasses import dataclass

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.nomination import NominationId
from fanfan.core.vo.participant import ParticipantId


@dataclass(slots=True, kw_only=True)
class Participant(AggregateRoot):
    id: ParticipantId
    cosplay2_id: int
    title: str
    nomination_id: NominationId
    voting_number: int | None
