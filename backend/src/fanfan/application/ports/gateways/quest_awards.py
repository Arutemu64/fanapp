from typing import Protocol

from fanfan.application.dto.page import CursorPagination
from fanfan.application.dto.quest import (
    LeaderboardEntryDTO,
    QuestAwardDTO,
    QuestPlayerDTO,
)
from fanfan.core.models.quest_award import QuestAward
from fanfan.core.vo.quest import QuestAwardId
from fanfan.core.vo.user import UserId


class QuestAwardGateway(Protocol):
    async def add(self, award: QuestAward) -> None: ...

    async def get(self, award_id: QuestAwardId) -> QuestAward | None: ...

    async def get_for_update(self, award_id: QuestAwardId) -> QuestAward | None: ...

    async def save(self, award: QuestAward) -> None: ...

    # Read projections (return DTOs, not aggregates)

    async def read_player(self, user_id: UserId) -> QuestPlayerDTO | None: ...

    async def read_players_by_username(
        self, search: str, limit: int
    ) -> list[QuestPlayerDTO]: ...

    async def read_leaderboard(
        self, *, limit: int, user_id: UserId
    ) -> tuple[list[LeaderboardEntryDTO], LeaderboardEntryDTO | None]:
        """The top ``limit`` players, then ``user_id``'s own entry.

        The own entry is None when the user has no points yet, and is returned
        even when the user is already in the top list.
        """
        ...

    async def read_awards_page(
        self, *, pagination: CursorPagination, awarded_by: UserId | None
    ) -> list[QuestAwardDTO]:
        """Newest first; ``awarded_by`` narrows to one staff member's awards."""
        ...
