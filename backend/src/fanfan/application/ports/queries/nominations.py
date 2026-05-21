from typing import Protocol

from fanfan.application.dto.nomination import NominationVotingDTO
from fanfan.application.dto.page import Pagination
from fanfan.core.vo.nomination import NominationCode
from fanfan.core.vo.user import UserId


class NominationQuery(Protocol):
    async def read_voting_dto(
        self, nomination_code: NominationCode, user_id: UserId | None = None
    ) -> NominationVotingDTO | None: ...

    async def read_list_votable_nominations(
        self,
        user_id: UserId | None = None,
        pagination: Pagination | None = None,
    ) -> list[NominationVotingDTO]: ...
