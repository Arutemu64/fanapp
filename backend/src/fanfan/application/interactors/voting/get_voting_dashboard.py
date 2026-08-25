from pydantic import BaseModel

from fanfan.application.dto.voting import NominationContenderDTO
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.vo.permission import Permission


class GetVotingDashboardOutput(BaseModel):
    voting_enabled: bool
    # Users who have voted in every votable nomination — the prize-draw pool.
    contest_pool_size: int
    nominations: list[NominationContenderDTO]


class GetVotingDashboard:
    """Organizer view of the running vote: the enable flag, the leader in each
    votable nomination, and the size of the prize-draw pool."""

    def __init__(
        self,
        app_settings_gateway: AppSettingsGateway,
        nomination_gateway: NominationGateway,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ) -> None:
        self.app_settings_gateway = app_settings_gateway
        self.nomination_gateway = nomination_gateway
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def __call__(self) -> GetVotingDashboardOutput:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.VOTING_MANAGE
        )

        settings = await self.app_settings_gateway.get()
        contenders = await self.nomination_gateway.read_voting_contenders()
        contest_pool_size = await self.user_gateway.count_voting_contest_pool()

        return GetVotingDashboardOutput(
            voting_enabled=settings.voting_enabled,
            contest_pool_size=contest_pool_size,
            nominations=contenders,
        )
