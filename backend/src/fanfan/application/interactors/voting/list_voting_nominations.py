from pydantic import BaseModel

from fanfan.application.dto.nomination import NominationVotingDTO
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.nominations import NominationRepository


class ListVotingNominationsOutput(BaseModel):
    nominations: list[NominationVotingDTO]


class ListVotingNominations:
    def __init__(
        self, nomination_repo: NominationRepository, id_provider: IdProvider
    ) -> None:
        self.nomination_repo = nomination_repo
        self.id_provider = id_provider

    async def __call__(self) -> ListVotingNominationsOutput:
        current_user_id = await self.id_provider.get_current_user_id()
        nominations = await self.nomination_repo.read_list_votable_nominations(
            user_id=current_user_id
        )
        return ListVotingNominationsOutput(nominations=nominations)
