from pydantic import BaseModel

from fanfan.application.dto.mailing import MailingDTO
from fanfan.application.dto.page import Pagination
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.vo.permission import Permission


class ListBroadcastsInput(BaseModel):
    pagination: Pagination


class ListBroadcastsOutput(BaseModel):
    mailings: list[MailingDTO]


class ListBroadcasts:
    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        mailing_gateway: MailingGateway,
        perm_service: PermissionService,
    ):
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
        mailings = await self.mailing_gateway.read_broadcasts(data.pagination)
        return ListBroadcastsOutput(mailings=mailings)
