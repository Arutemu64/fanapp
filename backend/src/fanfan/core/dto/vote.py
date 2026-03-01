from pydantic import BaseModel, ConfigDict

from fanfan.core.vo.participant import ParticipantId
from fanfan.core.vo.user import UserId
from fanfan.core.vo.vote import VoteId


class VoteBaseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: VoteId
    user_id: UserId
    participant_id: ParticipantId
