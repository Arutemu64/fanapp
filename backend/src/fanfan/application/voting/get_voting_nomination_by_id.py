from pydantic import BaseModel

from fanfan.adapters.db.gateways.nominations import NominationGateway
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.dto.nomination import NominationVotingDTO
from fanfan.core.exceptions.nominations import NominationNotFound
from fanfan.core.vo.nomination import NominationCode


class GetVotingNominationByIdCommand(BaseModel):
    nomination_code: NominationCode


class GetVotingNominationById:
    def __init__(
        self, nomination_gateway: NominationGateway, id_provider: IdProvider
    ) -> None:
        self.nomination_gateway = nomination_gateway
        self.id_provider = id_provider

    async def __call__(
        self, data: GetVotingNominationByIdCommand
    ) -> NominationVotingDTO:
        current_user_id = await self.id_provider.get_current_user_id()
        if nomination := await self.nomination_gateway.read_nomination_by_code(
            nomination_code=data.nomination_code, user_id=current_user_id
        ):
            return nomination
        raise NominationNotFound
