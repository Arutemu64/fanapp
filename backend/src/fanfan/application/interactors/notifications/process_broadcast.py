import logging

from pydantic import BaseModel

from fanfan.application.commands.notifications import CreateNotificationCommand
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
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
    ) -> None:
        self.user_gateway = user_gateway
        self.mailing_gateway = mailing_gateway
        self.uow = uow

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
        # SENDING and CreateNotification flips it to FINISHED on the last insert.
        mailing.begin_fan_out(len(recipient_ids))
        await self.mailing_gateway.save(mailing)

        # Queued in the same commit as SENDING, so the mailing never claims a
        # fan-out whose notifications were not queued.
        for user_id in recipient_ids:
            self.uow.enqueue(
                CreateNotificationCommand(
                    notification=NewNotification(
                        # Deterministic per (mailing, user): a rerun of this job
                        # queues the same ids, so CreateNotification's upsert
                        # no-ops instead of duplicating.
                        id=notification_id_for(data.mailing_id, user_id),
                        user_id=user_id,
                        title="Рассылка от организаторов",
                        body=data.body,
                        path="/notifications",
                        mailing_id=data.mailing_id,
                        type=NotificationType.BROADCAST,
                    )
                )
            )
        await self.uow.commit()
