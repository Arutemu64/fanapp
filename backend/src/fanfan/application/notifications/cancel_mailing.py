import logging
from dataclasses import dataclass

from fanfan.adapters.db.gateways.mailings import MailingGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.nats.events_broker import EventBroker
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.events.notifications import CancelMailingEvent
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.services.mailing import MailingService
from fanfan.core.vo.mailing import MailingId

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class CancelMailingDTO:
    mailing_id: MailingId


class CancelMailing:
    def __init__(
        self,
        mailing_gateway: MailingGateway,
        user_gateway: UserGateway,
        id_provider: IdProvider,
        events_broker: EventBroker,
        service: MailingService,
        uow: UnitOfWork,
    ):
        self.mailing_gateway = mailing_gateway
        self.user_gateway = user_gateway
        self.id_provider = id_provider
        self.events_broker = events_broker
        self.service = service
        self.uow = uow

    async def __call__(self, data: CancelMailingDTO) -> None:
        # TODO return do
        mailing = await self.mailing_gateway.get_mailing(data.mailing_id, lock=True)
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated
        current_user = await self.user_gateway.get_user_by_id(current_user_id)
        if current_user is None:
            raise UserNotFound
        self.service.ensure_user_can_cancel_mailing(mailing=mailing, user=current_user)
        async with self.uow:
            mailing.set_as_cancelled()
            await self.mailing_gateway.save_mailing(mailing)
            await self.uow.commit()
        await self.events_broker.publish(CancelMailingEvent(mailing_id=data.mailing_id))
        logger.info(
            "Mailing %s deleted by user %s",
            data.mailing_id,
            current_user.id,
            extra={"mailing": mailing},
        )
        return
