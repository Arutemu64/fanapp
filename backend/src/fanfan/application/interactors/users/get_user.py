from pydantic import BaseModel

from fanfan.application.dto.user import UserDetailsDTO
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.user import UserId


class GetUserInput(BaseModel):
    user_id: UserId


class GetUser:
    """Organiser view of one user: profile basics and linked external accounts."""

    def __init__(
        self,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ) -> None:
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def __call__(self, data: GetUserInput) -> UserDetailsDTO:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.USERS_READ
        )

        details = await self.user_gateway.read_user_details(data.user_id)
        if details is None:
            raise UserNotFound
        return details
