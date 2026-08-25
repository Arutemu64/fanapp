import logging

from pydantic import BaseModel

from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.settings import AppSettingsNotFound
from fanfan.core.vo.permission import Permission

logger = logging.getLogger(__name__)


class SetVotingEnabledInput(BaseModel):
    enabled: bool


class SetVotingEnabled:
    """Toggle whether visitors can vote. Split out from festival settings so
    running the vote is gated by voting:manage, not settings:manage."""

    def __init__(
        self,
        settings_gateway: AppSettingsGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        uow: UnitOfWork,
        realtime: RealtimeGateway,
    ) -> None:
        self.settings_gateway = settings_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.uow = uow
        self.realtime = realtime

    async def __call__(self, data: SetVotingEnabledInput) -> None:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.VOTING_MANAGE
        )

        settings = await self.settings_gateway.get_for_update()
        if settings is None:
            raise AppSettingsNotFound

        # No change means no write and no broadcast — a redundant refetch would
        # only churn every open client for identical state.
        if settings.voting_enabled == data.enabled:
            return

        settings.set_voting_enabled(enabled=data.enabled)
        await self.settings_gateway.save(settings)
        await self.uow.commit()
        logger.info(
            "Voting %s",
            "enabled" if data.enabled else "disabled",
            extra={"actor_id": str(current_user.id)},
        )

        # Published after commit, best-effort: voting availability rides the same
        # CONFIG_UPDATED signal the home page listens for, so a missed event
        # self-heals on the next /config load (reconnect, navigation, resume).
        await self.realtime.publish(SSEMessage(SSEEventName.CONFIG_UPDATED))
