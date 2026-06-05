from dataclasses import dataclass

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.nomination import NominationId
from fanfan.core.vo.participant import ParticipantId, ValueType


@dataclass(slots=True, kw_only=True)
class Participant(AggregateRoot):
    id: ParticipantId
    cosplay2_id: int
    title: str
    nomination_id: NominationId
    voting_number: int | None
    values: list[ParticipantValue]


@dataclass(slots=True, kw_only=True)
class ParticipantValue:
    title: str
    type: ValueType
    value: str | None
