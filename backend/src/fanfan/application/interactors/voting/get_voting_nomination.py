from pydantic import BaseModel, ConfigDict

from fanfan.application.dto.nomination import NominationVotingDTO
from fanfan.application.dto.participant import ParticipantFullDTO
from fanfan.application.ports.queries.nominations import NominationQuery
from fanfan.application.ports.queries.participants import ParticipantQuery
from fanfan.application.services.current_user import CurrentUserProvider
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
        participant_query: ParticipantQuery,
        nomination_query: NominationQuery,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.participant_query = participant_query
        self.nomination_query = nomination_query
        self.current_user_provider = current_user_provider

    async def __call__(
        self,
        data: GetVotingNominationInput,
    ) -> GetVotingNominationOutput:
        current_user_id = await self.current_user_provider.get_user_id()
        nomination = await self.nomination_query.read_voting_dto(
            nomination_code=data.nomination_code,
            user_id=current_user_id,
        )
        if nomination is None:
            raise NominationNotFound

        participants = await self.participant_query.read_list_participants(
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
