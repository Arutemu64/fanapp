import logging

from pydantic import BaseModel

from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.notifications import NotificationRevoked
from fanfan.core.vo.mailing import MailingId

logger = logging.getLogger(__name__)


class DeleteMailingMessagesInput(BaseModel):
    mailing_id: MailingId


class DeleteMailingMessages:
    def __init__(
        self,
        notification_gateway: NotificationGateway,
        events_broker: EventBroker,
        uow: UnitOfWork,
    ):
        self.notification_gateway = notification_gateway
        self.events_broker = events_broker
        self.uow = uow

    async def __call__(self, data: DeleteMailingMessagesInput) -> None:
        # Snapshot what to recall before deleting the rows: the revoke consumers
        # run asynchronously and would otherwise have nothing left to read.
        revocations = await self.notification_gateway.read_revocations_by_mailing_id(
            data.mailing_id
        )
        await self.notification_gateway.delete_all_by_mailing_id(data.mailing_id)
        await self.uow.commit()

        # Fan out one revoke per notification so each channel can apply its own
        # retry/backoff, mirroring how broadcasts fan out NotificationQueued.
        # Best-effort: already-delivered messages may be gone or out of reach.
        for revocation in revocations:
            await self.events_broker.publish(NotificationRevoked(revocation=revocation))

        logger.info(
            "Mailing notifications deleted, revoking %d delivered messages",
            len(revocations),
            extra={"mailing_id": str(data.mailing_id)},
        )
        return
