from typing import Protocol

from fanfan.application.dto.page import Pagination
from fanfan.application.dto.participant import ParticipantFullDTO
from fanfan.core.models.participant import Participant
from fanfan.core.vo.nomination import NominationId
from fanfan.core.vo.user import UserId


class ParticipantRepository(Protocol):
    async def add(self, participant: Participant) -> None: ...
    async def get_by_cosplay2_id(self, cosplay2_id: int) -> Participant | None: ...
    async def save(self, participant: Participant) -> None: ...
    async def delete(self, participant: Participant) -> None: ...

    async def read_list_participants(
        self,
        user_id: UserId,
        nomination_id: NominationId | None = None,
        search_query: str | None = None,
        pagination: Pagination | None = None,
    ) -> list[ParticipantFullDTO]: ...

    async def list_cosplay2_ids(self) -> list[int]: ...

    async def delete_by_cosplay2_ids(self, cosplay2_ids: list[int]) -> None: ...
