from pydantic import BaseModel, ConfigDict

from fanfan.core.vo.nomination import NominationCode, NominationId
from fanfan.core.vo.participant import ParticipantId


class ContenderDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    participant_id: ParticipantId
    title: str
    votes_count: int


class NominationContenderDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: NominationId
    code: NominationCode
    title: str
    is_votable: bool
    total_votes: int

    leader: ContenderDTO | None
