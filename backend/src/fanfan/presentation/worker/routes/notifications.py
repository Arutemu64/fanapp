import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta

from dishka import AsyncContainer

from fanfan.application.dto.jobs import Job
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
from fanfan.core.events.notifications import (
    BroadcastQueued,
    MailingCancelled,
    NotificationCreated,
    NotificationQueued,
)
from fanfan.core.exceptions.notifications import (
    MailingAlreadyCancelled,
    NotificationChannelUnavailable,
    NotificationRetryAfter,
    UserNotReachable,
)
from fanfan.core.vo.notification import NotificationId
from fanfan.presentation.worker.router import DiscardJob, JobRouter, RetryJob

logger = logging.getLogger(__name__)

notifications_router = JobRouter()


async def _deliver_to_channel(
    *,
    channel: str,
    notification_id: NotificationId,
    send: Callable[[SendNotificationInput], Awaitable[None]],
) -> None:
    """Drive one channel's send and translate the Notifier port's exceptions into
    job outcomes, so every channel honors the full contract the same way instead
    of each handler re-implementing (and drifting on) the set.
    """
    try:
        await send(SendNotificationInput(notification_id=notification_id))
    except NotificationRetryAfter as e:
        raise RetryJob(
            delay=timedelta(seconds=e.retry_after),
            reason=f"{channel} asked to retry later",
        ) from e
    except UserNotReachable as e:
        raise DiscardJob(reason=f"User not reachable on {channel}") from e
    except MailingAlreadyCancelled as e:
        raise DiscardJob(reason="Mailing was cancelled") from e
    except NotificationChannelUnavailable as e:
        # The whole channel is misconfigured (bad token, missing VAPID keys).
        # Retrying can't fix it, so drop the job instead.
        logger.warning(
            "%s channel unavailable — dropping notification %s",
            channel,
            notification_id,
        )
        raise DiscardJob(reason=f"{channel} channel unavailable") from e
    logger.info("Sent notification %s to %s", notification_id, channel)


@notifications_router.handler(NotificationQueued, name="create_notification")
async def create_notification(
    event: NotificationQueued, _job: Job, container: AsyncContainer
) -> None:
    interactor = await container.get(CreateNotification)
    try:
        await interactor(CreateNotificationInput(notification=event.notification))
    except MailingAlreadyCancelled as e:
        raise DiscardJob(reason="Mailing was cancelled") from e


@notifications_router.handler(NotificationCreated, name="send_notification_to_telegram")
async def send_notification_to_telegram(
    event: NotificationCreated, _job: Job, container: AsyncContainer
) -> None:
    interactor = await container.get(SendNotification)
    await _deliver_to_channel(
        channel="Telegram",
        notification_id=event.notification_id,
        send=interactor.send_notification_to_telegram,
    )


@notifications_router.handler(NotificationCreated, name="send_notification_to_vk")
async def send_notification_to_vk(
    event: NotificationCreated, _job: Job, container: AsyncContainer
) -> None:
    interactor = await container.get(SendNotification)
    await _deliver_to_channel(
        channel="VK",
        notification_id=event.notification_id,
        send=interactor.send_notification_to_vk,
    )


@notifications_router.handler(NotificationCreated, name="send_push_notification")
async def send_push_notification(
    event: NotificationCreated, _job: Job, container: AsyncContainer
) -> None:
    interactor = await container.get(SendNotification)
    await _deliver_to_channel(
        channel="push",
        notification_id=event.notification_id,
        send=interactor.send_notification_to_push,
    )


@notifications_router.handler(BroadcastQueued, name="process_broadcast")
async def process_broadcast(
    event: BroadcastQueued, _job: Job, container: AsyncContainer
) -> None:
    interactor = await container.get(ProcessBroadcast)
    await interactor(
        ProcessBroadcastInput(
            body=event.body,
            roles=event.roles,
            mailing_id=event.mailing_id,
        )
    )


@notifications_router.handler(MailingCancelled, name="cancel_mailing")
async def cancel_mailing(
    event: MailingCancelled, _job: Job, container: AsyncContainer
) -> None:
    interactor = await container.get(DeleteMailingNotifications)
    await interactor(DeleteMailingNotificationsInput(mailing_id=event.mailing_id))
