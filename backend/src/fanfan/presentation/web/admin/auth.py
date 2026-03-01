from typing import TYPE_CHECKING

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.vo.user import UserRole

if TYPE_CHECKING:
    from dishka import AsyncContainer


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        pass

    async def logout(self, request: Request) -> bool | RedirectResponse:
        pass

    async def authenticate(self, request: Request) -> bool | RedirectResponse:
        container: AsyncContainer = request.state.dishka_container
        id_provider = await container.get(IdProvider)
        current_user_id = await id_provider.get_current_user_id()
        if current_user_id is None:
            return False
        user_gateway = await container.get(UserGateway)
        current_user = await user_gateway.get_user_by_id(current_user_id)
        return bool(current_user and current_user.role == UserRole.ORG)
