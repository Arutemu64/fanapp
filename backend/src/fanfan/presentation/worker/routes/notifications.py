import logging
from collections.abc import Awaitable, Callable

from procrastinate import Blueprint

from fanfan.application.commands.notifications import (
    CancelMailingCommand,
    CreateNotificationCommand,
    ProcessBroadcastCommand,
)
from fanfan.application.interactors.notifications.create_notification import (
    CreateNotification,
    CreateNotificationInput,
)
from fanfan.application.interactors.notifications.delete_mailing_notifications import (
    DeleteMailingNotifications,
    DeleteMailingNotificationsInput,
)
from fanfan.application.interactors.notifications.process_broadcast import (
    ProcessBroadcast,
    ProcessBroadcastInput,
)
from fanfan.application.interactors.notifications.send_notification import (
    SendNotification,
    SendNotificationInput,
)
from fanfan.core.events.notifications import NotificationCreated
from fanfan.core.exceptions.notifications import (
    MailingAlreadyCancelled,
    NotificationChannelUnavailable,
    NotificationRetryAfter,
    UserNotReachable,
)
from fanfan.core.vo.notification import NotificationId
from fanfan.presentation.worker.subscriber import Delivery, subscriber

logger = logging.getLogger(__name__)

notifications_tasks = Blueprint()


async def _deliver_to_channel(
    *,
    channel: str,
    notification_id: NotificationId,
    send: Callable[[SendNotificationInput], Awaitable[None]],
) -> None:
    """Drive one channel's send and settle the Notifier port's exceptions, so
    every channel honors the full contract the same way instead of each task
    re-implementing (and drifting on) the set.

    Raising retries the job (presentation/worker/retry.py); returning settles it.
    """
    try:
        await send(SendNotificationInput(notification_id=notification_id))
    except NotificationRetryAfter as e:
        logger.warning(
            "Retry sending notification %s to %s in %s",
            notification_id,
            channel,
            e.retry_after,
        )
        raise
    except UserNotReachable:
        logger.info("Skip sending notification %s to %s", notification_id, channel)
    except MailingAlreadyCancelled:
        logger.info("Mailing for notification %s was cancelled", notification_id)
    except NotificationChannelUnavailable:
        # The whole channel is misconfigured (bad token, missing VAPID keys).
        # Retrying can't fix it, so settle the job instead of retrying.
        logger.warning(
            "%s channel unavailable — dropping notification %s",
            channel,
            notification_id,
        )
    else:
        logger.info("Sent notification %s to %s", notification_id, channel)


@subscriber(
    notifications_tasks, CreateNotificationCommand, name="create_new_notification"
)
async def create_new_notification(
    command: CreateNotificationCommand, delivery: Delivery
) -> None:
    interactor = await delivery.container.get(CreateNotification)
    try:
        await interactor(CreateNotificationInput(notification=command.notification))
    except MailingAlreadyCancelled:
        logger.info(
            "Mailing for notification %s was cancelled", command.notification.id
        )


@subscriber(
    notifications_tasks, NotificationCreated, name="send_notification_to_telegram"
)
async def send_notification_to_telegram(
    event: NotificationCreated, delivery: Delivery
) -> None:
    interactor = await delivery.container.get(SendNotification)
    await _deliver_to_channel(
        channel="Telegram",
        notification_id=event.notification_id,
        send=interactor.send_notification_to_telegram,
    )


@subscriber(notifications_tasks, NotificationCreated, name="send_notification_to_vk")
async def send_notification_to_vk(
    event: NotificationCreated, delivery: Delivery
) -> None:
    interactor = await delivery.container.get(SendNotification)
    await _deliver_to_channel(
        channel="VK",
        notification_id=event.notification_id,
        send=interactor.send_notification_to_vk,
    )


@subscriber(notifications_tasks, NotificationCreated, name="send_push_notification")
async def send_push_notification(
    event: NotificationCreated, delivery: Delivery
) -> None:
    interactor = await delivery.container.get(SendNotification)
    await _deliver_to_channel(
        channel="push",
        notification_id=event.notification_id,
        send=interactor.send_notification_to_push,
    )


@subscriber(notifications_tasks, ProcessBroadcastCommand, name="create_new_broadcast")
async def create_new_broadcast(
    command: ProcessBroadcastCommand, delivery: Delivery
) -> None:
    interactor = await delivery.container.get(ProcessBroadcast)
    await interactor(
        ProcessBroadcastInput(
            body=command.body,
            roles=command.roles,
            mailing_id=command.mailing_id,
        )
    )


@subscriber(notifications_tasks, CancelMailingCommand, name="cancel_mailing")
async def cancel_mailing(command: CancelMailingCommand, delivery: Delivery) -> None:
    interactor = await delivery.container.get(DeleteMailingNotifications)
    await interactor(DeleteMailingNotificationsInput(mailing_id=command.mailing_id))
