from typing import Protocol

from fanfan.application.dto.page import CursorPagination
from fanfan.application.dto.quest import (
    LeaderboardEntryDTO,
    QuestAwardDTO,
    QuestPlayerDTO,
)
from fanfan.core.models.quest_award import QuestAward
from fanfan.core.vo.quest import QuestAwardId
from fanfan.core.vo.user import UserId, UserNumber


class QuestAwardGateway(Protocol):
    async def add(self, award: QuestAward) -> None: ...

    async def get(self, award_id: QuestAwardId) -> QuestAward | None: ...

    async def get_for_update(self, award_id: QuestAwardId) -> QuestAward | None: ...

    async def save(self, award: QuestAward) -> None: ...

    # Read projections (return DTOs, not aggregates)

    async def read_player(self, number: UserNumber) -> QuestPlayerDTO | None: ...

    async def read_players_by_search(
        self, search: str, limit: int
    ) -> list[QuestPlayerDTO]:
        """Players whose username starts with ``search`` or whose number it is."""
        ...

    async def read_leaderboard(
        self, *, limit: int, user_id: UserId
    ) -> tuple[list[LeaderboardEntryDTO], LeaderboardEntryDTO | None]:
        """The top ``limit`` players, then ``user_id``'s own entry.

        The own entry is None when the user has no points yet, and is returned
        even when the user is already in the top list.
        """
        ...

    async def read_awards_page(
        self,
        *,
        pagination: CursorPagination,
        awarded_by: UserId | None = None,
        user_id: UserId | None = None,
    ) -> list[QuestAwardDTO]:
        """Newest first.

        ``awarded_by`` narrows to one staff member's awards, ``user_id`` to one
        player's.
        """
        ...
