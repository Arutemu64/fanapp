import logging

from pydantic import MISSING, AwareDatetime, BaseModel, Field

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
    enabled: bool | MISSING = MISSING
    max_award: int | MISSING = Field(default=MISSING, ge=1, le=10_000)
    cancel_window_minutes: int | MISSING = Field(default=MISSING, ge=0, le=1440)


class UpdateAppSettingsInput(BaseModel):
    """A partial update, nested like AppSettingsDTO: omitted fields stay as is."""

    # Omitted is MISSING rather than None so that an explicit null is a 422: JSON
    # Merge Patch (RFC 7396) reads null as "remove", and none of these fields can
    # be cleared, so accepting it as "leave as is" would be a silent no-op.

    # Require an offset: the range check compares an incoming boundary against the
    # persisted (tz-aware) counterpart, and a naive value would raise TypeError —
    # a 500 — instead of a clean 422. The organizer form always sends an instant.
    festival_start: AwareDatetime | MISSING = MISSING
    festival_end: AwareDatetime | MISSING = MISSING
    quest: UpdateQuestInput | MISSING = MISSING


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

        if data.festival_start is not MISSING or data.festival_end is not MISSING:
            # PATCH may carry either boundary alone, so validate the range as a
            # whole — filling the untouched side from the persisted value — rather
            # than each field in isolation, which could reject a valid shift of both.
            new_start = settings.festival_start
            if data.festival_start is not MISSING:
                new_start = data.festival_start
            new_end = settings.festival_end
            if data.festival_end is not MISSING:
                new_end = data.festival_end
            settings.set_festival_schedule(start=new_start, end=new_end)
            update_flag = True
            public_config_changed = True

        if data.quest is not MISSING and data.quest.model_fields_set:
            quest = data.quest
            # The switch and the cap are public; the cancel window is not.
            if quest.enabled is not MISSING or quest.max_award is not MISSING:
                public_config_changed = True
            # model_dump leaves out MISSING fields, which update_quest reads as
            # "leave as is".
            settings.update_quest(**quest.model_dump())
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
