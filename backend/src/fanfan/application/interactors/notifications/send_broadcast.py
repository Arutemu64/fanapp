import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.models.mailing import Mailing
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.permission import PermissionName, Permissions
from fanfan.core.vo.user import UserRole

logger = logging.getLogger(__name__)


class SendBroadcastInput(BaseModel):
    body: str
    roles: list[UserRole]


class SendBroadcastOutput(BaseModel):
    mailing_id: MailingId


class SendBroadcast:
    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        user_gateway: UserGateway,
        mailing_gateway: MailingGateway,
        perm_service: PermissionService,
        uow: UnitOfWork,
    ):
        self.current_user_provider = current_user_provider
        self.user_gateway = user_gateway
        self.mailing_gateway = mailing_gateway
        self.perm_service = perm_service
        self.uow = uow

    async def __call__(self, data: SendBroadcastInput) -> SendBroadcastOutput:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, perm_name=PermissionName(Permissions.NOTIFICATIONS_SEND)
        )

        # Record BroadcastQueued on the mailing so it lands in the outbox in the
        # same transaction as the row — no dual write between commit and publish.
        mailing = Mailing.create(by_user_id=current_user.id)
        mailing.queue_broadcast(body=data.body, roles=data.roles)
        await self.mailing_gateway.add(mailing)
        await self.uow.commit()

        logger.info(
            "New broadcast %s initiated by user %s",
            mailing.id,
            current_user.id,
        )
        return SendBroadcastOutput(mailing_id=mailing.id)
