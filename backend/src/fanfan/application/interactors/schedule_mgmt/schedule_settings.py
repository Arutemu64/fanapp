import logging
from dataclasses import replace

from pydantic import MISSING, BaseModel, Field

from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.vo.permission import Permission

logger = logging.getLogger(__name__)


class ScheduleSettingsDTO(BaseModel):
    # Seconds an operator waits between two announced schedule edits.
    announcement_timeout: int = Field(ge=1)
    changeover_seconds: int = Field(ge=0, le=600)


class UpdateScheduleSettingsInput(BaseModel):
    # Partial, like UpdateAppSettingsInput: an omitted field is left as is, so
    # an older client that doesn't know a newer field can't reset it. MISSING
    # rather than None, so an explicit null is a 422, not a silent no-op.
    announcement_timeout: int | MISSING = Field(default=MISSING, ge=1)
    changeover_seconds: int | MISSING = Field(default=MISSING, ge=0, le=600)


# Guarded by schedule:setup, not settings:manage, the way the voting time range
# lives in AppSettings but is managed under voting:manage: the schedule tool
# holds everything that shapes the programme, so one grant opens all of it.
class GetScheduleSettings:
    def __init__(
        self,
        app_settings_gateway: AppSettingsGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ) -> None:
        self.app_settings_gateway = app_settings_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def __call__(self) -> ScheduleSettingsDTO:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.SCHEDULE_SETUP
        )

        settings = await self.app_settings_gateway.get()
        return ScheduleSettingsDTO(
            announcement_timeout=settings.limits.announcement_timeout,
            changeover_seconds=settings.schedule.changeover_seconds,
        )


class UpdateScheduleSettings:
    def __init__(
        self,
        app_settings_gateway: AppSettingsGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        uow: UnitOfWork,
        realtime: RealtimeGateway,
    ) -> None:
        self.app_settings_gateway = app_settings_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.uow = uow
        self.realtime = realtime

    async def __call__(self, data: UpdateScheduleSettingsInput) -> None:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.SCHEDULE_SETUP
        )

        settings = await self.app_settings_gateway.get_for_update()
        changeover_changed = (
            data.changeover_seconds is not MISSING
            and data.changeover_seconds != settings.schedule.changeover_seconds
        )
        if data.announcement_timeout is not MISSING:
            settings.set_limits(
                replace(settings.limits, announcement_timeout=data.announcement_timeout)
            )
        if data.changeover_seconds is not MISSING:
            settings.set_schedule(
                replace(settings.schedule, changeover_seconds=data.changeover_seconds)
            )
        await self.app_settings_gateway.save(settings)
        await self.uow.commit()
        logger.info(
            "Schedule settings updated",
            extra={"actor_id": str(current_user.id)},
        )

        # The changeover is in GET /config (the wait estimates use it); the
        # cooldown is not, so only a changeover edit sends clients to refetch.
        # Published after commit, best-effort, like UpdateSettings.
        if changeover_changed:
            await self.realtime.publish(SSEMessage(SSEEventName.CONFIG_UPDATED))
