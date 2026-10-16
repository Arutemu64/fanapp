import logging
from typing import Annotated

from pydantic import BaseModel, Field
from pydantic.types import UuidVersion

from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.notifications import MailingAlreadyExists
from fanfan.core.models.mailing import Mailing
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.user import UserRole

logger = logging.getLogger(__name__)


class SendBroadcastInput(BaseModel):
    # Client-generated so a retry after a lost response replays the broadcast
    # instead of sending it to everyone twice (docs/adr/0034). Version 7 keeps
    # the IDs time-ordered like the server-generated ones.
    mailing_id: Annotated[
        MailingId,
        UuidVersion(7),
        Field(description="UUIDv7 the client generates once per broadcast form."),
    ]
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
    ) -> None:
        self.current_user_provider = current_user_provider
        self.user_gateway = user_gateway
        self.mailing_gateway = mailing_gateway
        self.perm_service = perm_service
        self.uow = uow

    async def __call__(self, data: SendBroadcastInput) -> SendBroadcastOutput:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.NOTIFICATIONS_SEND
        )

        existing = await self.mailing_gateway.get(data.mailing_id)
        if existing is not None:
            if not existing.is_broadcast(
                by_user_id=current_user.id, body=data.body, roles=data.roles
            ):
                raise MailingAlreadyExists
            logger.info(
                "Broadcast replayed",
                extra={
                    "mailing_id": str(existing.id),
                    "actor_id": str(current_user.id),
                },
            )
            return SendBroadcastOutput(mailing_id=existing.id)

        # Record BroadcastQueued on the mailing so it lands in the outbox in the
        # same transaction as the row — no dual write between commit and publish.
        mailing = Mailing.create(by_user_id=current_user.id, mailing_id=data.mailing_id)
        mailing.queue_broadcast(body=data.body, roles=data.roles)
        await self.mailing_gateway.add(mailing)
        await self.uow.commit()

        logger.info(
            "Broadcast initiated",
            extra={
                "mailing_id": str(mailing.id),
                "actor_id": str(current_user.id),
            },
        )
        return SendBroadcastOutput(mailing_id=mailing.id)
