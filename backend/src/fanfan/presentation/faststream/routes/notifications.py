from dishka import FromDishka
from dishka_faststream import inject
from faststream import AckPolicy, Logger
from faststream.nats import NatsMessage, NatsRouter, PullSub

from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.application.interactors.notifications.create_notification import (
    CreateNotification,
    CreateNotificationInput,
)
from fanfan.application.interactors.notifications.delete_mailing_messages import (
    DeleteMailingMessages,
    DeleteMailingMessagesInput,
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
from fanfan.presentation.faststream.jstream import stream

notifications_router = NatsRouter()


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
async def create_new_notification(
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
    try:
        await interactor.send_notification_to_telegram(
            SendNotificationInput(notification_id=data.notification_id)
        )
    except NotificationRetryAfter as e:
        logger.warning(
            "Retry sending notification %s to Telegram in %s",
            data.notification_id,
            e.retry_after,
        )
        await msg.nack(delay=e.retry_after)
        return
    except UserNotReachable:
        logger.info("Skip sending notification %s to Telegram", data.notification_id)
        await msg.reject()
        return
    except MailingAlreadyCancelled:
        logger.info("Mailing for notification %s was cancelled", data.notification_id)
        await msg.reject()
        return
    else:
        await msg.ack()
        logger.info("Sent notification %s to Telegram", data.notification_id)

    return


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
    try:
        await interactor.send_notification_to_push(
            SendNotificationInput(notification_id=data.notification_id)
        )
    except MailingAlreadyCancelled:
        logger.info("Mailing for notification %s was cancelled", data.notification_id)
        await msg.reject()
        return
    except NotificationChannelUnavailable:
        # Push channel is misconfigured (missing/invalid VAPID keys). Retrying
        # can't fix it, so drop the message instead of redelivering forever.
        logger.warning(
            "Push channel unavailable — dropping notification %s",
            data.notification_id,
        )
        await msg.reject()
        return
    else:
        await msg.ack()
        logger.info("Sent notification %s to push", data.notification_id)

    return


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
    return


@notifications_router.subscriber(
    MailingCancelled.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="cancel_mailing",
)
@inject
async def cancel_mailing(
    data: MailingCancelled,
    interactor: FromDishka[DeleteMailingMessages],
) -> None:

    await interactor(DeleteMailingMessagesInput(mailing_id=data.mailing_id))
    return
