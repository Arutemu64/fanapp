from pydantic import BaseModel

from fanfan.application.dto.schedule_change import ScheduleChangeFullDTO
from fanfan.application.ports.gateways.schedule_changes import (
    ScheduleChangeGateway,
)
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.vo.permission import PermissionName, Permissions


class ListScheduleChangesResult(BaseModel):
    schedule_changes: list[ScheduleChangeFullDTO]


class ListScheduleChanges:
    def __init__(
        self,
        schedule_change_gateway: ScheduleChangeGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ):
        self.schedule_change_gateway = schedule_change_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def __call__(self) -> ListScheduleChangesResult:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, perm_name=PermissionName(Permissions.SCHEDULE_MANAGE)
        )
        schedule_changes = (
            await self.schedule_change_gateway.read_list_schedule_changes()
        )
        return ListScheduleChangesResult(schedule_changes=schedule_changes)
