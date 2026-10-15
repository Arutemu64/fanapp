from pydantic import BaseModel

from fanfan.application.dto.page import CursorPagination, cut_page
from fanfan.application.dto.user import UserListFilter, UserListItemDTO
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.vo.permission import Permission


class ListUsersInput(BaseModel):
    pagination: CursorPagination
    user_filter: UserListFilter = UserListFilter()


class ListUsersOutput(BaseModel):
    users: list[UserListItemDTO]
    # Total matching the current filter, so the client can say how many it
    # found without walking every page.
    total: int
    next_cursor: str | None


class ListUsers:
    """Newest-first, filterable directory of all users for organizers."""

    def __init__(
        self,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ) -> None:
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def __call__(self, data: ListUsersInput) -> ListUsersOutput:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.USERS_READ
        )

        rows = await self.user_gateway.read_users_page(
            pagination=data.pagination, user_filter=data.user_filter
        )
        users, next_cursor = cut_page(rows, data.pagination)
        total = await self.user_gateway.count_users(user_filter=data.user_filter)
        return ListUsersOutput(users=users, total=total, next_cursor=next_cursor)
