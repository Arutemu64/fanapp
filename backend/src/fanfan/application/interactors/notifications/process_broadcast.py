import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.notification_fan_out import NotificationFanOut
from fanfan.core.exceptions.notifications import MailingAlreadyCancelled
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
            # The fan-out finishes the mailing with its last chunk, or at once
            # when the broadcast reaches nobody.
            await self.fan_out(notifications, mailing_id=data.mailing_id)
        except MailingAlreadyCancelled:
            logger.info("Broadcast %s was cancelled", data.mailing_id)

    async def abandon(self, mailing_id: MailingId) -> None:
        """Fail the mailing of a fan-out that will not be retried again."""
        # The failed run can leave the transaction aborted.
        await self.uow.rollback()
        mailing = await self.mailing_gateway.get(mailing_id)
        if mailing is None:
            return
        mailing.mark_failed()
        await self.mailing_gateway.save(mailing)
        await self.uow.commit()
