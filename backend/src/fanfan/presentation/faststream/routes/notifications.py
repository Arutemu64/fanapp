from collections.abc import Awaitable, Callable

from dishka import FromDishka
from dishka_faststream import inject
from faststream import AckPolicy, Logger
from faststream.nats import NatsMessage, NatsRouter, PullSub
from nats.js.api import ConsumerConfig

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

# AckWait for the external-send channels, in seconds: how long JetStream waits
# for an ack before it redelivers. It must clear a send's own client-timeout
# ceiling so a slow-but-live send is not redelivered mid-flight (the default 30s
# would be) — Telegram ~60s (aiogram default session), VK up to ~60s (send +
# delete, 30s each), and push 10s per device, which for the one or two devices a
# real user has is ~10-20s. Only a user with ~9+ simultaneously-slow push
# subscriptions could outlast this window; that redelivers, but the consumers are
# idempotent and push collapses the duplicate by its `tag`, so the extra send is
# harmless — not worth a heartbeat to prevent. No head-of-line blocking either:
# NATS processes one message per durable at a time (no max_workers), so a slow
# send only delays its own channel's queue, bounded by the client timeout.
_SEND_ACK_WAIT_SECONDS = 90.0


async def _deliver_to_channel(
    *,
    channel: str,
    notification_id: NotificationId,
    send: Callable[[SendNotificationInput], Awaitable[None]],
    msg: NatsMessage,
    logger: Logger,
) -> None:
    """Drive one channel's send and translate the Notifier port's exceptions into
    JetStream ack decisions, so every channel honors the full contract the same
    way instead of each subscriber re-implementing (and drifting on) the set.
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
    config=ConsumerConfig(ack_wait=_SEND_ACK_WAIT_SECONDS),
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
        send=interactor.send_notification_to_telegram,
        msg=msg,
        logger=logger,
    )


@notifications_router.subscriber(
    NotificationCreated.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="send_notification_to_vk",
    ack_policy=AckPolicy.MANUAL,
    config=ConsumerConfig(ack_wait=_SEND_ACK_WAIT_SECONDS),
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
        send=interactor.send_notification_to_vk,
        msg=msg,
        logger=logger,
    )


@notifications_router.subscriber(
    NotificationCreated.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="send_push_notification",
    ack_policy=AckPolicy.MANUAL,
    config=ConsumerConfig(ack_wait=_SEND_ACK_WAIT_SECONDS),
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
        send=interactor.send_notification_to_push,
        msg=msg,
        logger=logger,
    )


@notifications_router.subscriber(
    BroadcastQueued.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="create_new_broadcast",
    # Redeliver on failure rather than TERM: this stream's guarantee is
    # redelivery + idempotent consumers (see jstream.py), so a transient blip
    # mid-broadcast must not silently drop a whole mailing. The default
    # REJECT_ON_ERROR would discard it permanently.
    ack_policy=AckPolicy.NACK_ON_ERROR,
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
    # Same as create_new_broadcast: redeliver on a transient failure instead of
    # TERMing, so a cancellation is not lost while notifications keep going out.
    ack_policy=AckPolicy.NACK_ON_ERROR,
)
@inject
async def cancel_mailing(
    data: MailingCancelled,
    interactor: FromDishka[DeleteMailingNotifications],
) -> None:
    await interactor(DeleteMailingNotificationsInput(mailing_id=data.mailing_id))
