from pydantic import BaseModel

from fanfan.adapters.db.gateways.nominations import NominationGateway
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.dto.nomination import NominationVotingDTO


class ListVotingNominationsResult(BaseModel):
    nominations: list[NominationVotingDTO]


class ListVotingNominations:
    def __init__(
        self, nomination_gateway: NominationGateway, id_provider: IdProvider
    ) -> None:
        self.nomination_gateway = nomination_gateway
        self.id_provider = id_provider

    async def __call__(self) -> ListVotingNominationsResult:
        current_user_id = await self.id_provider.get_current_user_id()
        nominations = await self.nomination_gateway.read_list_votable_nominations(
            user_id=current_user_id
        )
        return ListVotingNominationsResult(nominations=nominations)
