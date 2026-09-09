import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.notifications import MailingNotFound
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.permission import Permission

logger = logging.getLogger(__name__)


class CancelMailingInput(BaseModel):
    mailing_id: MailingId


class CancelMailing:
    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        mailing_gateway: MailingGateway,
        perm_service: PermissionService,
        uow: UnitOfWork,
    ):
        self.current_user_provider = current_user_provider
        self.mailing_gateway = mailing_gateway
        self.perm_service = perm_service
        self.uow = uow

    async def __call__(self, data: CancelMailingInput) -> None:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.NOTIFICATIONS_SEND
        )

        # get() locks the row and registers the aggregate with the UoW, so the
        # MailingCancelled event recorded by cancel() lands in the outbox in the
        # same transaction as the status flip. cancel() raises if the mailing is
        # already cancelled or has reached a terminal state.
        mailing = await self.mailing_gateway.get(data.mailing_id)
        if mailing is None:
            raise MailingNotFound
        mailing.cancel()
        # Flip the status synchronously (get() returns a detached domain object,
        # so the transition is not otherwise persisted): this stops in-flight
        # sends via ensure_active() without waiting for the async event consumer.
        await self.mailing_gateway.set_status(
            mailing_id=mailing.id, status=mailing.status
        )
        await self.uow.commit()

        logger.info(
            "Mailing cancellation requested",
            extra={
                "mailing_id": str(mailing.id),
                "actor_id": str(current_user.id),
            },
        )
