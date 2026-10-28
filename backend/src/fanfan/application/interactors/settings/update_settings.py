import logging
from typing import Annotated

from pydantic import MISSING, AwareDatetime, Field

from fanfan.application.dto.input import InputModel
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


class UpdateAppSettingsInput(InputModel):
    festival_starts_at: AwareDatetime | MISSING = MISSING
    festival_ends_at: AwareDatetime | MISSING = MISSING
    quest_enabled: bool | MISSING = MISSING
    quest_max_award: Annotated[int, Field(ge=1, le=10_000)] | MISSING = MISSING
    quest_cancel_window_minutes: Annotated[int, Field(ge=0, le=1440)] | MISSING = (
        MISSING
    )


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
        data_to_update = data.model_dump()
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.SETTINGS_MANAGE
        )
        settings = await self.settings_gateway.get_for_update()
        if settings is None:
            raise AppSettingsNotFound

        update_flag = False
        public_config_changed = False

        festival_starts_at = data_to_update.get("festival_starts_at")
        festival_ends_at = data_to_update.get("festival_ends_at")
        if festival_starts_at is not None or festival_ends_at is not None:
            new_start = festival_starts_at or settings.festival_starts_at
            new_end = festival_ends_at or settings.festival_ends_at
            settings.set_festival_schedule(start=new_start, end=new_end)
            update_flag = True
            public_config_changed = True

        quest_enabled = data_to_update.get("quest_enabled")
        quest_max_award = data_to_update.get("quest_max_award")
        quest_cancel_window = data_to_update.get("quest_cancel_window_minutes")
        quest_touched = (
            quest_enabled is not None
            or quest_max_award is not None
            or quest_cancel_window is not None
        )
        if quest_touched:
            if quest_enabled is not None or quest_max_award is not None:
                public_config_changed = True
            settings.update_quest(
                enabled=quest_enabled,
                max_award=quest_max_award,
                cancel_window_minutes=quest_cancel_window,
            )
            update_flag = True

        if not update_flag:
            return

        await self.settings_gateway.save(settings)
        await self.uow.commit()
        logger.info(
            "Festival settings updated",
            extra={"actor_id": str(current_user.id)},
        )

        if public_config_changed:
            await self.realtime.publish(SSEMessage(SSEEventName.CONFIG_UPDATED))
