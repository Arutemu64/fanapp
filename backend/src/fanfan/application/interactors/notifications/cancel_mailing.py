import logging

from pydantic import BaseModel

from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.events.notifications import MailingCancelled
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.notifications import MailingNotFound
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.permission import Permission

logger = logging.getLogger(__name__)


class CancelMailingInput(BaseModel):
    mailing_id: MailingId


class CancelMailing:
    def __init__(
        self,
        mailing_gateway: MailingGateway,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        events_broker: EventBroker,
        uow: UnitOfWork,
    ):
        self.mailing_gateway = mailing_gateway
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.events_broker = events_broker
        self.uow = uow

    async def __call__(self, data: CancelMailingInput) -> None:
        mailing = await self.mailing_gateway.get(data.mailing_id)
        if mailing is None:
            raise MailingNotFound
        current_user = await self.current_user_provider.require_user()
        # Owners can always cancel their own mailing; everyone else needs the
        # broadcast permission to cancel someone else's.
        if mailing.by_user_id != current_user.id:
            try:
                await self.perm_service.ensure(
                    user=current_user,
                    permission=Permission.NOTIFICATIONS_SEND,
                )
            except AccessDenied:
                raise AccessDenied(
                    details={"reason": "MAILING_DELETE_FORBIDDEN"}
                ) from None
        mailing.set_as_cancelled()
        await self.mailing_gateway.save(mailing)
        await self.uow.commit()
        await self.events_broker.publish(MailingCancelled(mailing_id=data.mailing_id))
        logger.info(
            "Mailing cancelled",
            extra={
                "mailing_id": str(data.mailing_id),
                "actor_id": str(current_user.id),
            },
        )
