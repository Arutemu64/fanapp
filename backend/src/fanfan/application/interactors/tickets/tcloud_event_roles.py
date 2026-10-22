import logging

from pydantic import BaseModel, Field, TypeAdapter

from fanfan.application.dto.ticket import TCloudEventRoleDTO
from fanfan.application.interactors.sync.get_sync_sources import (
    AvailableSyncSources,
)
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.etag import compute_strong_etag
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.settings import TCloudEventRolesChanged
from fanfan.core.models.app_settings import AppSettings
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.sync import SyncSource

logger = logging.getLogger(__name__)


class TCloudEventRolesOutput(BaseModel):
    # False when this deployment has no TicketsCloud credentials: the mapping
    # is kept, but nothing imports tickets to apply it to.
    available: bool
    event_roles: list[TCloudEventRoleDTO]
    # Strong entity-tag of event_roles, for If-Match on the PUT; see
    # AppSettingsDTO.etag for why it travels in the body.
    etag: str


class SetTCloudEventRolesInput(BaseModel):
    # A list rather than an object keyed by event id, so the form's row order
    # survives the round trip. A repeated event id keeps its last role.
    event_roles: list[TCloudEventRoleDTO] = Field(max_length=100)


_EVENT_ROLES = TypeAdapter(list[TCloudEventRoleDTO])


def _read_event_roles(settings: AppSettings) -> list[TCloudEventRoleDTO]:
    return [
        TCloudEventRoleDTO(event_id=event_id, role=role)
        for event_id, role in settings.tickets.tcloud_event_roles.items()
    ]


def _event_roles_etag(event_roles: list[TCloudEventRoleDTO]) -> str:
    # Hashes the mapping alone: `available` is deployment config, and a save
    # cannot change it, so it must not turn an open form stale.
    return compute_strong_etag(_EVENT_ROLES.dump_json(event_roles).decode())


def _read_output(settings: AppSettings, *, available: bool) -> TCloudEventRolesOutput:
    event_roles = _read_event_roles(settings)
    return TCloudEventRolesOutput(
        available=available,
        event_roles=event_roles,
        etag=_event_roles_etag(event_roles),
    )


# Guarded by tickets:manage, not settings:manage, the way the voting time range
# lives in AppSettings but is managed under voting:manage: the mapping decides
# which role a bought ticket grants, the same power as generating one.
class GetTCloudEventRoles:
    def __init__(
        self,
        app_settings_gateway: AppSettingsGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        available_sources: AvailableSyncSources,
    ) -> None:
        self.app_settings_gateway = app_settings_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.available_sources = available_sources

    async def __call__(self) -> TCloudEventRolesOutput:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.TICKETS_MANAGE
        )

        settings = await self.app_settings_gateway.get()
        return _read_output(
            settings, available=SyncSource.TCLOUD in self.available_sources
        )


class SetTCloudEventRoles:
    def __init__(
        self,
        app_settings_gateway: AppSettingsGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        uow: UnitOfWork,
        available_sources: AvailableSyncSources,
    ) -> None:
        self.app_settings_gateway = app_settings_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.uow = uow
        self.available_sources = available_sources

    async def __call__(
        self,
        data: SetTCloudEventRolesInput,
        if_match: frozenset[str] | None,
    ) -> TCloudEventRolesOutput:
        """Replace the mapping the caller read at the version ``if_match`` names.

        ``if_match`` holds the entity-tags the caller accepts, or None to write
        unconditionally. Checked under the row lock, like UpdateSettings: the
        PUT replaces the whole mapping, so a save from a stale form would drop
        every row another organizer added in between.
        """
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.TICKETS_MANAGE
        )

        settings = await self.app_settings_gateway.get_for_update()
        current_etag = _event_roles_etag(_read_event_roles(settings))
        if if_match is not None and current_etag not in if_match:
            raise TCloudEventRolesChanged
        settings.set_tcloud_event_roles(
            {item.event_id: item.role for item in data.event_roles}
        )
        await self.app_settings_gateway.save(settings)
        await self.uow.commit()
        # Applies to tickets imported from now on; tickets already stored keep
        # the role they were imported with.
        logger.info(
            "TicketsCloud event roles updated",
            extra={
                "actor_id": str(current_user.id),
                "events": len(settings.tickets.tcloud_event_roles),
            },
        )
        return _read_output(
            settings, available=SyncSource.TCLOUD in self.available_sources
        )
