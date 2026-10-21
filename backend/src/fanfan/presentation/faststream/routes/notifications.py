from collections.abc import Awaitable, Callable

from dishka import FromDishka
from dishka_faststream import inject
from faststream import AckPolicy, Logger
from faststream.nats import NatsMessage, NatsRouter, PullSub

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
    NotificationExpired,
    NotificationRetryAfter,
    UserNotReachable,
)
from fanfan.core.vo.notification import NotificationId
from fanfan.presentation.faststream.jstream import stream
from fanfan.presentation.faststream.redelivery import (
    consumer_config,
    in_progress_heartbeat,
)

notifications_router = NatsRouter()

# AckWait for the external-send channels, in seconds: how long JetStream waits
# for an ack before it redelivers. It must clear a send's own client-timeout
# ceiling so a slow-but-live send is not redelivered mid-flight (the default 30s
# would be) — Telegram ~60s (aiogram default session), VK up to ~60s (send +
# delete, 30s each), and push 10s per device, sent to a user's devices at once.
# The channel rate limiters (adapters/rate_limiter.py) wait before a send, so a
# burst queued behind one adds to this; at the worker counts below that wait
# stays under a second.
_SEND_ACK_WAIT_SECONDS = 90.0

# Sends in flight per channel. One at a time, a channel delivers a mailing at
# the speed of one round trip to its provider (a push service answers in ~0.1-
# 0.3s), so a schedule change reaching a thousand people would take minutes.
# FastStream runs this many handlers of one durable concurrently
# (ConcurrentPullStreamSubscriber, picked when max_workers > 1 with pull_sub).
# Push has no published rate limit, so it gets the most; Telegram (~30
# messages/s, https://core.telegram.org/bots/faq) and VK (20 requests/s for a
# community token, https://dev.vk.ru/ru/api/api-requests) are paced by their
# rate limiters, and a few workers are enough to keep those busy. Every worker
# holds a pooled DB connection only for its reads, never across the send, so
# these can exceed the faststream DB pool.
_PUSH_WORKERS = 32
_TELEGRAM_WORKERS = 8
_VK_WORKERS = 8

# Messages per pull request. With the default of one, every message costs its
# own request to NATS; a batch keeps the workers fed in fewer round trips.
_SEND_PULL_BATCH = 16


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
    except NotificationExpired:
        logger.info(
            "Notification %s expired before reaching %s", notification_id, channel
        )
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
    CreateNotificationCommand.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="create_new_notification",
    ack_policy=AckPolicy.MANUAL,
    config=consumer_config(),
)
@inject
async def create_new_notification(
    data: CreateNotificationCommand,
    interactor: FromDishka[CreateNotification],
    msg: NatsMessage,
) -> None:
    try:
        await interactor(CreateNotificationInput(notification=data.notification))
    except MailingAlreadyCancelled:
        await msg.reject()
        raise
    await msg.ack()


@notifications_router.subscriber(
    NotificationCreated.subject,
    stream=stream,
    pull_sub=PullSub(batch_size=_SEND_PULL_BATCH),
    max_workers=_TELEGRAM_WORKERS,
    durable="send_notification_to_telegram",
    ack_policy=AckPolicy.MANUAL,
    config=consumer_config(ack_wait=_SEND_ACK_WAIT_SECONDS),
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
    pull_sub=PullSub(batch_size=_SEND_PULL_BATCH),
    max_workers=_VK_WORKERS,
    durable="send_notification_to_vk",
    ack_policy=AckPolicy.MANUAL,
    config=consumer_config(ack_wait=_SEND_ACK_WAIT_SECONDS),
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
    pull_sub=PullSub(batch_size=_SEND_PULL_BATCH),
    max_workers=_PUSH_WORKERS,
    durable="send_push_notification",
    ack_policy=AckPolicy.MANUAL,
    config=consumer_config(ack_wait=_SEND_ACK_WAIT_SECONDS),
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
    ProcessBroadcastCommand.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="create_new_broadcast",
    # Redeliver on failure rather than TERM: this stream's guarantee is
    # redelivery + idempotent consumers (see jstream.py), so a transient blip
    # mid-broadcast must not silently drop a whole mailing. The default
    # REJECT_ON_ERROR would discard it permanently.
    ack_policy=AckPolicy.NACK_ON_ERROR,
    config=consumer_config(),
)
@inject
async def create_new_broadcast(
    data: ProcessBroadcastCommand,
    interactor: FromDishka[ProcessBroadcast],
    msg: NatsMessage,
) -> None:
    # A large fan-out can outlast AckWait while NATS is slow to ack; the
    # heartbeat keeps a live run from being redelivered on top of itself.
    async with in_progress_heartbeat(msg):
        await interactor(
            ProcessBroadcastInput(
                body=data.body,
                roles=data.roles,
                mailing_id=data.mailing_id,
            )
        )


@notifications_router.subscriber(
    CancelMailingCommand.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="cancel_mailing",
    # Same as create_new_broadcast: redeliver on a transient failure instead of
    # TERMing, so a cancellation is not lost while notifications keep going out.
    ack_policy=AckPolicy.NACK_ON_ERROR,
    config=consumer_config(),
)
@inject
async def cancel_mailing(
    data: CancelMailingCommand,
    interactor: FromDishka[DeleteMailingNotifications],
) -> None:
    await interactor(DeleteMailingNotificationsInput(mailing_id=data.mailing_id))
