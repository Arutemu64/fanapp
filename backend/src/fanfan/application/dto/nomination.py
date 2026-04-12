from pydantic import BaseModel, ConfigDict

from fanfan.core.vo.nomination import NominationCode, NominationId
from fanfan.core.vo.participant import ParticipantId
from fanfan.core.vo.vote import VoteId


class NominationBaseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: NominationId
    code: NominationCode
    title: str


class NominationVoteDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: VoteId
    participant_id: ParticipantId


class NominationVotingDTO(NominationBaseDTO):
    model_config = ConfigDict(from_attributes=True)

    participants_count: int

    # User-specific values
    user_vote: NominationVoteDTO | None
