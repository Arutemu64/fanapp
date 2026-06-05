from typing import Protocol

from fanfan.application.dto.participant import ParticipantFullDTO
from fanfan.core.vo.nomination import NominationId
from fanfan.core.vo.user import UserId


class ParticipantQuery(Protocol):
    async def read_list_participants(
        self,
        user_id: UserId | None = None,
        nomination_id: NominationId | None = None,
    ) -> list[ParticipantFullDTO]: ...
