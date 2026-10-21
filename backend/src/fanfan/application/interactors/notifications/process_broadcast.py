import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.notification_fan_out import NotificationFanOut
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
        mailing_gateway: MailingGateway,
        uow: UnitOfWork,
        fan_out: NotificationFanOut,
    ) -> None:
        self.user_gateway = user_gateway
        self.mailing_gateway = mailing_gateway
        self.uow = uow
        self.fan_out = fan_out

    async def __call__(self, data: ProcessBroadcastInput) -> None:
        recipient_ids = await self.user_gateway.read_ids_by_roles(*data.roles)
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

        # With no recipients the mailing finishes at once; otherwise it moves to
        # SENDING and the fan-out flips it to FINISHED on the last insert.
        mailing.begin_fan_out(len(recipient_ids))
        await self.mailing_gateway.save(mailing)
        await self.uow.commit()

        notifications = [
            NewNotification(
                # Deterministic per (mailing, user): a redelivered trigger reruns
                # this with the same ids, so the insert no-ops instead of
                # duplicating.
                id=notification_id_for(data.mailing_id, user_id),
                user_id=user_id,
                title="Рассылка от организаторов",
                body=data.body,
                path="/notifications",
                mailing_id=data.mailing_id,
                type=NotificationType.BROADCAST,
            )
            for user_id in recipient_ids
        ]
        try:
            await self.fan_out(notifications)
        except MailingAlreadyCancelled:
            logger.info("Broadcast %s was cancelled during fan-out", mailing.id)
