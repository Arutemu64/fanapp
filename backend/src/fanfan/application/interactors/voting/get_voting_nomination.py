from pydantic import BaseModel, ConfigDict

from fanfan.application.dto.nomination import NominationVotingDTO
from fanfan.application.dto.participant import ParticipantFullDTO
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.nominations import NominationRepository
from fanfan.application.ports.repositories.participants import ParticipantRepository
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.nominations import NominationNotFound
from fanfan.core.vo.nomination import NominationCode


class GetVotingNominationInput(BaseModel):
    nomination_code: NominationCode


class GetVotingNominationOutput(NominationVotingDTO):
    model_config = ConfigDict(from_attributes=True)

    participants: list[ParticipantFullDTO]


class GetVotingNomination:
    def __init__(
        self,
        participant_repo: ParticipantRepository,
        nomination_repo: NominationRepository,
        id_provider: IdProvider,
    ) -> None:
        self.participant_repo = participant_repo
        self.nomination_repo = nomination_repo
        self.id_provider = id_provider

    async def __call__(
        self,
        data: GetVotingNominationInput,
    ) -> GetVotingNominationOutput:
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated
        nomination = await self.nomination_repo.read_voting_dto(
            nomination_code=data.nomination_code,
            user_id=current_user_id,
        )
        if nomination is None:
            raise NominationNotFound

        participants = await self.participant_repo.read_list_participants(
            user_id=current_user_id,
            nomination_id=nomination.id,
        )

        return GetVotingNominationOutput(
            id=nomination.id,
            code=nomination.code,
            title=nomination.title,
            user_vote=nomination.user_vote,
            participants_count=nomination.participants_count,
            participants=participants,
        )
