import logging

from pydantic import BaseModel

from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.notifications import NotificationQueued
from fanfan.core.exceptions.notifications import (
    MailingAlreadyCancelled,
    MailingNotFound,
)
from fanfan.core.models.notification import NewNotification
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationType, notification_id_for
from fanfan.core.vo.user import UserRole

logger = logging.getLogger(__name__)


class ProcessBroadcastInput(BaseModel):
    mailing_id: MailingId
    body: str
    roles: list[UserRole]


class ProcessBroadcast:
    def __init__(
        self,
        user_gateway: UserGateway,
        events_broker: EventBroker,
        mailing_gateway: MailingGateway,
        uow: UnitOfWork,
    ):
        self.user_gateway = user_gateway
        self.events_broker = events_broker
        self.mailing_gateway = mailing_gateway
        self.uow = uow

    async def __call__(self, data: ProcessBroadcastInput):
        users = await self.user_gateway.read_all_by_roles(*data.roles)
        mailing = await self.mailing_gateway.get(data.mailing_id)
        if mailing is None:
            raise MailingNotFound

        try:
            # Cancelled between creation and this (at-least-once) fan-out trigger:
            # stop here rather than queue notifications that would be rejected.
            mailing.ensure_active()
        except MailingAlreadyCancelled:
            logger.info("Broadcast %s was cancelled before fan-out", mailing.id)
            return

        await self.mailing_gateway.set_total(
            mailing_id=mailing.id, total_count=len(users)
        )
        # No recipients means the mailing is already done; otherwise it moves to
        # SENDING and CreateNotification flips it to FINISHED on the last insert.
        if users:
            mailing.start_sending()
        else:
            mailing.mark_finished()
        await self.mailing_gateway.set_status(
            mailing_id=mailing.id, status=mailing.status
        )
        await self.uow.commit()

        events = [
            NotificationQueued(
                notification=NewNotification(
                    # Deterministic per (mailing, user): a redelivered
                    # NotificationQueued reruns this with the same id, so the
                    # gateway upsert below no-ops instead of duplicating.
                    id=notification_id_for(data.mailing_id, u.id),
                    user_id=u.id,
                    title="Рассылка от организаторов",
                    body=data.body,
                    path="/notifications",
                    mailing_id=data.mailing_id,
                    type=NotificationType.BROADCAST,
                )
            )
            for u in users
        ]
        for e in events:
            await self.events_broker.publish(e)
