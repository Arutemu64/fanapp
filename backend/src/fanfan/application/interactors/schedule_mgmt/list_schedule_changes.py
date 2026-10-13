from pydantic import BaseModel

from fanfan.application.dto.page import CursorPagination, cut_page
from fanfan.application.dto.schedule_change import ScheduleChangeFullDTO
from fanfan.application.ports.gateways.schedule_changes import (
    ScheduleChangeGateway,
)
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.vo.permission import Permission


class ListScheduleChangesInput(BaseModel):
    pagination: CursorPagination


class ListScheduleChangesOutput(BaseModel):
    schedule_changes: list[ScheduleChangeFullDTO]
    next_cursor: str | None


class ListScheduleChanges:
    def __init__(
        self,
        schedule_change_gateway: ScheduleChangeGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ) -> None:
        self.schedule_change_gateway = schedule_change_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def __call__(
        self, data: ListScheduleChangesInput
    ) -> ListScheduleChangesOutput:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.SCHEDULE_MANAGE
        )
        rows = await self.schedule_change_gateway.read_list_schedule_changes(
            pagination=data.pagination
        )
        schedule_changes, next_cursor = cut_page(rows, data.pagination)
        return ListScheduleChangesOutput(
            schedule_changes=schedule_changes, next_cursor=next_cursor
        )
