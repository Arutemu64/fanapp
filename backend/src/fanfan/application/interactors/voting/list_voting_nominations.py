from pydantic import BaseModel

from fanfan.application.dto.nomination import NominationVotingDTO
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.services.current_user import CurrentUserProvider


class ListVotingNominationsOutput(BaseModel):
    nominations: list[NominationVotingDTO]


class ListVotingNominations:
    def __init__(
        self,
        nomination_query: NominationGateway,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.nomination_query = nomination_query
        self.current_user_provider = current_user_provider

    async def __call__(self) -> ListVotingNominationsOutput:
        current_user_id = await self.current_user_provider.get_user_id()
        nominations = await self.nomination_query.read_list_votable_nominations(
            user_id=current_user_id
        )
        return ListVotingNominationsOutput(nominations=nominations)
