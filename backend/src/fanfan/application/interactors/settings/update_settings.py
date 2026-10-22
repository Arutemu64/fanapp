import logging
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, Field

from fanfan.application.dto.patch import NOT_NULL
from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.application.dto.settings import AppSettingsDTO
from fanfan.application.interactors.settings.get_settings import read_app_settings
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.settings import AppSettingsChanged, AppSettingsNotFound
from fanfan.core.vo.permission import Permission

logger = logging.getLogger(__name__)


class UpdateQuestInput(BaseModel):
    enabled: Annotated[bool | None, NOT_NULL] = None
    max_award: Annotated[int | None, NOT_NULL] = Field(default=None, ge=1, le=10_000)
    cancel_window_minutes: Annotated[int | None, NOT_NULL] = Field(
        default=None, ge=0, le=1440
    )


class UpdateAppSettingsInput(BaseModel):
    """A partial update, nested like AppSettingsDTO: omitted fields stay as is."""

    # Require an offset: the range check compares an incoming boundary against the
    # persisted (tz-aware) counterpart, and a naive value would raise TypeError —
    # a 500 — instead of a clean 422. The organizer form always sends an instant.
    festival_start: Annotated[AwareDatetime | None, NOT_NULL] = None
    festival_end: Annotated[AwareDatetime | None, NOT_NULL] = None
    # A default instance rather than None keeps null a plain type error and the
    # schema free of a nullable union.
    quest: UpdateQuestInput = Field(default_factory=UpdateQuestInput)


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

    async def __call__(
        self,
        data: UpdateAppSettingsInput,
        if_match: frozenset[str] | None,
    ) -> AppSettingsDTO:
        """Apply a partial update made against the version ``if_match`` names.

        ``if_match`` holds the entity-tags the caller accepts, or None to write
        unconditionally. The check runs under the row lock, so two organizers
        saving the same stale form cannot both pass it (RFC 9110 §13.1.1).
        """
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.SETTINGS_MANAGE
        )
        settings = await self.settings_gateway.get_for_update()
        if settings is None:
            raise AppSettingsNotFound
        if if_match is not None and read_app_settings(settings).etag not in if_match:
            raise AppSettingsChanged

        update_flag = False
        # Tracks changes to fields exposed by GET /config, so the CONFIG_UPDATED
        # broadcast fires only when a public-facing value actually moved — a
        # cancel-window-only edit would send every client to refetch identical
        # config.
        public_config_changed = False

        if data.festival_start is not None or data.festival_end is not None:
            # PATCH may carry either boundary alone, so validate the range as a
            # whole — filling the untouched side from the persisted value — rather
            # than each field in isolation, which could reject a valid shift of both.
            # A datetime is always truthy, so `or` picks the persisted value only
            # when this PATCH left the boundary out.
            new_start = data.festival_start or settings.festival_start
            new_end = data.festival_end or settings.festival_end
            settings.set_festival_schedule(start=new_start, end=new_end)
            update_flag = True
            public_config_changed = True

        quest = data.quest
        if quest.model_fields_set:
            # The switch and the cap are public; the cancel window is not.
            if quest.enabled is not None or quest.max_award is not None:
                public_config_changed = True
            settings.update_quest(
                enabled=quest.enabled,
                max_award=quest.max_award,
                cancel_window_minutes=quest.cancel_window_minutes,
            )
            update_flag = True

        if not update_flag:
            return read_app_settings(settings)

        await self.settings_gateway.save(settings)
        await self.uow.commit()
        logger.info(
            "Festival settings updated",
            extra={"actor_id": str(current_user.id)},
        )

        # Published after commit: SSE carries no committed state, and a live update
        # for a rolled-back change would send clients to refetch config that never
        # moved. Best-effort like the schedule live update — a missed event self-heals
        # on the next /config load (reconnect, navigation, or app resume).
        if public_config_changed:
            await self.realtime.publish(SSEMessage(SSEEventName.CONFIG_UPDATED))

        return read_app_settings(settings)
