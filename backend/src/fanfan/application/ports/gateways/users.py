from typing import Protocol

from fanfan.application.dto.page import CursorPagination
from fanfan.application.dto.user import (
    CurrentUserDTO,
    UserBaseDTO,
    UserDetailsDTO,
    UserListFilter,
    UserListItemDTO,
)
from fanfan.core.models.user import User
from fanfan.core.vo.user import UserId, UserNumber, UserRole


class UserGateway(Protocol):
    async def add(self, user: User) -> None: ...
    async def get_by_id(self, user_id: UserId) -> User | None: ...
    async def get_by_number(self, number: UserNumber) -> User | None: ...
    async def get_by_username(self, username: str) -> User | None: ...
    async def get_by_email(self, email: str) -> User | None: ...
    async def save(self, user: User) -> None: ...

    async def read_current_user(self, user_id: UserId) -> CurrentUserDTO | None: ...

    # Fan-out reads return bare ids: a mailing can target most of the table,
    # and recipients need nothing else, so hydrating full users is waste.
    async def read_ids_by_roles(self, *roles: UserRole) -> list[UserId]: ...

    # The prize-draw pool: users who have voted in every votable nomination.
    # Computed on request from the votes table (see the SQL adapter), so a draw
    # always reflects who is eligible right now.
    async def count_voting_contest_pool(self) -> int: ...

    # Draw a random winner together with the size of the pool they came from,
    # evaluated in a single statement so a vote committing mid-draw cannot make
    # the two describe different snapshots. Winner is None on an empty pool.
    async def draw_voting_contest_winner(self) -> tuple[UserBaseDTO | None, int]: ...

    async def read_ids_receiving_all_announcements(self) -> list[UserId]: ...

    async def read_schedule_editors(self) -> list[UserBaseDTO]: ...

    # Newest first, read with pagination.fetch_limit for cut_page. count_users
    # applies the same filter, so the total matches what the pages add up to.
    async def read_users_page(
        self, *, pagination: CursorPagination, user_filter: UserListFilter
    ) -> list[UserListItemDTO]: ...

    async def count_users(self, *, user_filter: UserListFilter) -> int: ...

    async def read_user_details(self, user_id: UserId) -> UserDetailsDTO | None: ...
