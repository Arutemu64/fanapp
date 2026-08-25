from pydantic import BaseModel

from fanfan.application.dto.page import Pagination
from fanfan.application.dto.user import UserListItemDTO
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.vo.permission import Permission


class ListUsersInput(BaseModel):
    pagination: Pagination
    search: str | None = None


class ListUsersResult(BaseModel):
    users: list[UserListItemDTO]
    # Total matching the current search, so the client can render page controls
    # without walking every page.
    total: int


class ListUsers:
    """Paginated, searchable directory of all users for organisers."""

    def __init__(
        self,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ) -> None:
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def __call__(self, data: ListUsersInput) -> ListUsersResult:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.USERS_READ
        )

        users = await self.user_gateway.read_users_page(
            pagination=data.pagination, search=data.search
        )
        total = await self.user_gateway.count_users(search=data.search)
        return ListUsersResult(users=users, total=total)
