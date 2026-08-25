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
    total_votes: int

    # The participant leading this nomination, or None while nobody has voted yet
    # (no participants, or every participant on zero votes — there is no honest
    # "leader" to name).
    leader: ContenderDTO | None
