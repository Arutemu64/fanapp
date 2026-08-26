import logging

from pydantic import AwareDatetime, BaseModel

from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.settings import AppSettingsNotFound
from fanfan.core.vo.permission import Permission

logger = logging.getLogger(__name__)


class SetVotingTimeRangeInput(BaseModel):
    # Require an offset: the stored range is later compared against an aware clock
    # in AppSettings.is_voting_open(now), so a persisted naive bound would raise
    # TypeError on every voting-status check, not just here. The dashboard form
    # always sends an instant.
    voting_start: AwareDatetime | None
    voting_end: AwareDatetime | None


class SetVotingTimeRange:
    """Set the time range during which visitors can vote. Split out from
    festival settings so running the vote is gated by voting:manage, not
    settings:manage."""

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

    async def __call__(self, data: SetVotingTimeRangeInput) -> None:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.VOTING_MANAGE
        )

        settings = await self.settings_gateway.get_for_update()
        if settings is None:
            raise AppSettingsNotFound

        if (
            settings.voting_start == data.voting_start
            and settings.voting_end == data.voting_end
        ):
            return

        settings.set_voting_time_range(start=data.voting_start, end=data.voting_end)
        await self.settings_gateway.save(settings)
        await self.uow.commit()
        logger.info(
            "Voting time range updated: %s – %s",
            data.voting_start,
            data.voting_end,
            extra={"actor_id": str(current_user.id)},
        )

        # Published after commit, best-effort: voting availability rides the same
        # CONFIG_UPDATED signal the home page listens for, so a missed event
        # self-heals on the next /config load (reconnect, navigation, resume).
        await self.realtime.publish(SSEMessage(SSEEventName.CONFIG_UPDATED))
