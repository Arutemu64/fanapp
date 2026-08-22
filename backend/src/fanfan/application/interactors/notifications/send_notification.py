import logging
from typing import TypeVar

from pydantic import BaseModel

from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.notifier import (
    Notifier,
    PushNotifierPort,
    TelegramNotifierPort,
    VkNotifierPort,
)
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.notifications import (
    MailingAlreadyCancelled,
    MailingNotFound,
    NotificationNotFound,
)
from fanfan.core.models.notification import Notification
from fanfan.core.vo.mailing import MailingStatus
from fanfan.core.vo.notification import NotificationId

logger = logging.getLogger(__name__)

_TargetT = TypeVar("_TargetT")


class SendNotificationInput(BaseModel):
    notification_id: NotificationId


class SendNotification:
    def __init__(
        self,
        mailing_gateway: MailingGateway,
        notification_gateway: NotificationGateway,
        tg_notifier: TelegramNotifierPort,
        push_notifier: PushNotifierPort,
        vk_notifier: VkNotifierPort,
        uow: UnitOfWork,
    ):
        self.mailing_gateway = mailing_gateway
        self.notification_gateway = notification_gateway
        self.tg_notifier = tg_notifier
        self.push_notifier = push_notifier
        self.vk_notifier = vk_notifier
        self.uow = uow

    async def _get_notification(self, data: SendNotificationInput) -> Notification:
        notification = await self.notification_gateway.get(data.notification_id)
        if notification is None:
            raise NotificationNotFound
        if notification.mailing_id:
            # Read the mailing without locking it. Sending is read-only towards
            # the mailing — we only gate on whether it was cancelled — so a plain
            # read observes the status; taking SELECT ... FOR UPDATE here would
            # serialize every send fanning out one mailing on that row.
            mailing = await self.mailing_gateway.read_mailing(notification.mailing_id)
            if mailing is None:
                raise MailingNotFound
            if mailing.status is MailingStatus.CANCELLED:
                raise MailingAlreadyCancelled
        return notification

    async def _prepare(
        self, data: SendNotificationInput, notifier: Notifier[_TargetT]
    ) -> tuple[Notification, _TargetT]:
        # Do every DB read the send needs — the notification, its mailing, and
        # the channel recipient — then end the read transaction here, in the use
        # case that owns the transaction boundary, before any network I/O. The
        # send path persists nothing, so rolling back releases the pooled
        # connection (and the notification's FOR UPDATE lock) for the duration of
        # the send; holding it across the network round-trip would, fanning out
        # one mailing, pin a connection per in-flight notification and exhaust
        # the pool.
        notification = await self._get_notification(data)
        target = await notifier.resolve(notification)
        await self.uow.rollback()
        return notification, target

    async def send_notification_to_telegram(self, data: SendNotificationInput) -> None:
        notification, target = await self._prepare(data, self.tg_notifier)
        await self.tg_notifier.deliver(notification, target)

    async def send_notification_to_push(self, data: SendNotificationInput) -> None:
        notification, target = await self._prepare(data, self.push_notifier)
        await self.push_notifier.deliver(notification, target)

    async def send_notification_to_vk(self, data: SendNotificationInput) -> None:
        notification, target = await self._prepare(data, self.vk_notifier)
        await self.vk_notifier.deliver(notification, target)
