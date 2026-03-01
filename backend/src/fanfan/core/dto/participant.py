from pydantic import BaseModel, ConfigDict

from fanfan.core.vo.participant import ParticipantId, ParticipantVotingNumber
from fanfan.core.vo.vote import VoteId


class ParticipantBaseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: ParticipantId
    title: str
    voting_number: ParticipantVotingNumber | None


class ParticipantVoteDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: VoteId


class ParticipantFullDTO(ParticipantBaseDTO):
    model_config = ConfigDict(from_attributes=True)

    # Calculated values
    votes_count: int

    # User-specific values
    user_vote: ParticipantVoteDTO | None
