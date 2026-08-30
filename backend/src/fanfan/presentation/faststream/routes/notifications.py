from collections.abc import Awaitable, Callable

from dishka import FromDishka
from dishka_faststream import inject
from faststream import AckPolicy, Logger
from faststream.nats import NatsMessage, NatsRouter, PullSub

from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.application.interactors.notifications.create_notification import (
    CreateNotification,
    CreateNotificationInput,
)
from fanfan.application.interactors.notifications.delete_mailing_notifications import (
    DeleteMailingNotifications,
    DeleteMailingNotificationsInput,
)
from fanfan.application.interactors.notifications.get_notification import (
    GetNotification,
    GetNotificationInput,
)
from fanfan.application.interactors.notifications.process_broadcast import (
    ProcessBroadcast,
    ProcessBroadcastInput,
)
from fanfan.application.interactors.notifications.send_notification import (
    SendNotification,
    SendNotificationInput,
)
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.core.events.notifications import (
    BroadcastQueued,
    MailingCancelled,
    NotificationCreated,
    NotificationQueued,
)
from fanfan.core.exceptions.notifications import (
    MailingAlreadyCancelled,
    NotificationChannelUnavailable,
    NotificationNotFound,
    NotificationRetryAfter,
    UserNotReachable,
)
from fanfan.core.vo.notification import NotificationId
from fanfan.presentation.faststream.jstream import stream

notifications_router = NatsRouter()


async def _deliver_to_channel(
    *,
    channel: str,
    notification_id: NotificationId,
    deliver: Callable[[], Awaitable[None]],
    msg: NatsMessage,
    logger: Logger,
) -> None:
    """Drive one channel's send and translate the Notifier port's exceptions into
    JetStream ack decisions, so every channel honors the full contract the same
    way instead of each subscriber re-implementing (and drifting on) the set.
    """
    try:
        await deliver()
    except NotificationRetryAfter as e:
        logger.warning(
            "Retry sending notification %s to %s in %s",
            notification_id,
            channel,
            e.retry_after,
        )
        await msg.nack(delay=e.retry_after)
    except UserNotReachable:
        logger.info("Skip sending notification %s to %s", notification_id, channel)
        await msg.reject()
    except MailingAlreadyCancelled:
        logger.info("Mailing for notification %s was cancelled", notification_id)
        await msg.reject()
    except NotificationChannelUnavailable:
        # The whole channel is misconfigured (bad token, missing VAPID keys).
        # Retrying can't fix it, so drop the message instead of redelivering.
        logger.warning(
            "%s channel unavailable — dropping notification %s",
            channel,
            notification_id,
        )
        await msg.reject()
    else:
        await msg.ack()
        logger.info("Sent notification %s to %s", notification_id, channel)


@notifications_router.subscriber(
    NotificationQueued.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="create_new_notification",
    ack_policy=AckPolicy.MANUAL,
)
@notifications_router.publisher(
    subject=NotificationCreated.subject,
    stream=stream,
)
@inject
async def create_new_notification(  # noqa: PLR0913, PLR0917 — all params framework-injected
    data: NotificationQueued,
    interactor: FromDishka[CreateNotification],
    get_notification: FromDishka[GetNotification],
    realtime_gateway: FromDishka[RealtimeGateway],
    msg: NatsMessage,
    logger: Logger,
) -> NotificationCreated:
    try:
        notification_id = await interactor(
            CreateNotificationInput(notification=data.notification)
        )
    except MailingAlreadyCancelled:
        await msg.reject()
        raise
    else:
        await msg.ack()

        try:
            notification = await get_notification(
                GetNotificationInput(notification_id=notification_id)
            )
            await realtime_gateway.publish(
                SSEMessage(
                    SSEEventName.NOTIFICATION_CREATED,
                    data=notification.model_dump(mode="json"),
                ),
                user_id=data.notification.user_id,
            )
        except NotificationNotFound:
            logger.warning(
                "Notification %s was created but could not be loaded "
                "for realtime delivery",
                notification_id,
            )
        except Exception:
            logger.exception(
                "Failed to publish realtime notification %s",
                notification_id,
            )

        return NotificationCreated(notification_id=notification_id)


@notifications_router.subscriber(
    NotificationCreated.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="send_notification_to_telegram",
    ack_policy=AckPolicy.MANUAL,
)
@inject
async def send_notification_to_telegram(
    data: NotificationCreated,
    interactor: FromDishka[SendNotification],
    msg: NatsMessage,
    logger: Logger,
) -> None:
    await _deliver_to_channel(
        channel="Telegram",
        notification_id=data.notification_id,
        deliver=lambda: interactor.send_notification_to_telegram(
            SendNotificationInput(notification_id=data.notification_id)
        ),
        msg=msg,
        logger=logger,
    )


@notifications_router.subscriber(
    NotificationCreated.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="send_notification_to_vk",
    ack_policy=AckPolicy.MANUAL,
)
@inject
async def send_notification_to_vk(
    data: NotificationCreated,
    interactor: FromDishka[SendNotification],
    msg: NatsMessage,
    logger: Logger,
) -> None:
    await _deliver_to_channel(
        channel="VK",
        notification_id=data.notification_id,
        deliver=lambda: interactor.send_notification_to_vk(
            SendNotificationInput(notification_id=data.notification_id)
        ),
        msg=msg,
        logger=logger,
    )


@notifications_router.subscriber(
    NotificationCreated.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="send_push_notification",
    ack_policy=AckPolicy.MANUAL,
)
@inject
async def send_push_notification(
    data: NotificationCreated,
    interactor: FromDishka[SendNotification],
    msg: NatsMessage,
    logger: Logger,
) -> None:
    await _deliver_to_channel(
        channel="push",
        notification_id=data.notification_id,
        deliver=lambda: interactor.send_notification_to_push(
            SendNotificationInput(notification_id=data.notification_id)
        ),
        msg=msg,
        logger=logger,
    )


@notifications_router.subscriber(
    BroadcastQueued.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="create_new_broadcast",
)
@inject
async def create_new_broadcast(
    data: BroadcastQueued,
    interactor: FromDishka[ProcessBroadcast],
) -> None:
    await interactor(
        ProcessBroadcastInput(
            body=data.body,
            roles=data.roles,
            mailing_id=data.mailing_id,
        )
    )


@notifications_router.subscriber(
    MailingCancelled.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="cancel_mailing",
)
@inject
async def cancel_mailing(
    data: MailingCancelled,
    interactor: FromDishka[DeleteMailingNotifications],
) -> None:
    await interactor(DeleteMailingNotificationsInput(mailing_id=data.mailing_id))
