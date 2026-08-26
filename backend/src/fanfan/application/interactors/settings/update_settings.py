import logging

from pydantic import AwareDatetime, BaseModel, Field

from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.settings import AppSettingsNotFound
from fanfan.core.vo.permission import Permission

logger = logging.getLogger(__name__)


class UpdateAppSettingsInput(BaseModel):
    # Require an offset: the range check compares an incoming boundary against the
    # persisted (tz-aware) counterpart, and a naive value would raise TypeError —
    # a 500 — instead of a clean 422. The organizer form always sends an instant.
    festival_start: AwareDatetime | None = None
    festival_end: AwareDatetime | None = None
    announcement_timeout: int | None = Field(default=None, ge=1)


class UpdateSettings:
    def __init__(
        self,
        settings_gateway: AppSettingsGateway,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        uow: UnitOfWork,
        realtime: RealtimeGateway,
    ) -> None:
        self.settings_gateway = settings_gateway
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.uow = uow
        self.realtime = realtime

    async def __call__(self, data: UpdateAppSettingsInput) -> None:
        data_to_update = data.model_dump(exclude_unset=True)
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.SETTINGS_MANAGE
        )
        settings = await self.settings_gateway.get_for_update()
        if settings is None:
            raise AppSettingsNotFound

        update_flag = False
        # Tracks changes to fields exposed by GET /config, so the CONFIG_UPDATED
        # broadcast fires only when a public-facing value actually moved — a
        # limits-only edit would send every client to refetch identical config.
        public_config_changed = False

        festival_start = data_to_update.get("festival_start")
        festival_end = data_to_update.get("festival_end")
        if festival_start is not None or festival_end is not None:
            # PATCH may carry either boundary alone, so validate the range as a
            # whole — filling the untouched side from the persisted value — rather
            # than each field in isolation, which could reject a valid shift of both.
            settings.set_festival_schedule(
                start=festival_start
                if festival_start is not None
                else settings.festival_start,
                end=festival_end if festival_end is not None else settings.festival_end,
            )
            update_flag = True
            public_config_changed = True

        if (
            announcement_timeout := data_to_update.get("announcement_timeout")
        ) is not None:
            settings.update_limits(announcement_timeout=announcement_timeout)
            update_flag = True

        if not update_flag:
            return

        await self.settings_gateway.save(settings)
        await self.uow.commit()
        logger.info(
            "Festival settings updated",
            extra={"actor_id": str(current_user.id)},
        )

        # Published after commit: SSE carries no committed state, and a broadcast
        # for a rolled-back change would send clients to refetch config that never
        # moved. Best-effort like the schedule broadcast — a missed event self-heals
        # on the next /config load (reconnect, navigation, or app resume).
        if public_config_changed:
            await self.realtime.publish(SSEMessage(SSEEventName.CONFIG_UPDATED))
