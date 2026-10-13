from pydantic import BaseModel

from fanfan.application.dto.mailing import MailingDTO
from fanfan.application.dto.page import CursorPagination, cut_page
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.vo.permission import Permission


class ListBroadcastsInput(BaseModel):
    pagination: CursorPagination


class ListBroadcastsOutput(BaseModel):
    mailings: list[MailingDTO]
    next_cursor: str | None


class ListBroadcasts:
    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        mailing_gateway: MailingGateway,
        perm_service: PermissionService,
    ) -> None:
        self.current_user_provider = current_user_provider
        self.mailing_gateway = mailing_gateway
        self.perm_service = perm_service

    async def __call__(self, data: ListBroadcastsInput) -> ListBroadcastsOutput:
        # Same gate as sending: the mailing history is a broadcaster tool, so it
        # shows every organizer's broadcasts (not scoped to the current user).
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.NOTIFICATIONS_SEND
        )
        rows = await self.mailing_gateway.read_broadcasts(data.pagination)
        mailings, next_cursor = cut_page(rows, data.pagination)
        return ListBroadcastsOutput(mailings=mailings, next_cursor=next_cursor)
