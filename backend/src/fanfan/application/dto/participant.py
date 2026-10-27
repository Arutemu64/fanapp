from pydantic import BaseModel, ConfigDict

from fanfan.core.vo.participant import ParticipantId
from fanfan.core.vo.vote import VoteId


class ParticipantBaseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: ParticipantId
    title: str
    voting_number: int | None


class ParticipantVoteDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: VoteId


class ParticipantFullDTO(ParticipantBaseDTO):
    model_config = ConfigDict(from_attributes=True)

    votes_count: int

    user_vote: ParticipantVoteDTO | None
