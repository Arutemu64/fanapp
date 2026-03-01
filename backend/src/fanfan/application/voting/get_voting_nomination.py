from pydantic import BaseModel, ConfigDict

from fanfan.adapters.db.gateways.nominations import NominationGateway
from fanfan.adapters.db.gateways.participants import ParticipantGateway
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.dto.nomination import NominationVotingDTO
from fanfan.core.dto.participant import ParticipantFullDTO


class GetVotingNominationCommand(BaseModel):
    nomination_code: str


class GetVotingNominationResult(NominationVotingDTO):
    model_config = ConfigDict(from_attributes=True)

    participants: list[ParticipantFullDTO]


class GetVotingNomination:
    def __init__(
        self,
        participant_gateway: ParticipantGateway,
        nomination_gateway: NominationGateway,
        id_provider: IdProvider,
    ) -> None:
        self.participant_gateway = participant_gateway
        self.nomination_gateway = nomination_gateway
        self.id_provider = id_provider

    async def __call__(
        self,
        data: GetVotingNominationCommand,
    ) -> GetVotingNominationResult:
        current_user_id = await self.id_provider.get_current_user_id()
        nomination = await self.nomination_gateway.read_nomination_by_code(
            nomination_code=data.nomination_code,
            user_id=current_user_id,
        )
        participants = (
            await self.participant_gateway.list_participants_by_nomination_id(
                user_id=current_user_id,
                nomination_id=nomination.id,
            )
        )

        return GetVotingNominationResult(
            id=nomination.id,
            code=nomination.code,
            title=nomination.title,
            user_vote=nomination.user_vote,
            participants_count=nomination.participants_count,
            participants=participants,
        )
