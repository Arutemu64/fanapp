from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Path, Query

from fanfan.application.dto.page import Pagination
from fanfan.application.interactors.notifications.cancel_mailing import (
    CancelMailing,
    CancelMailingInput,
)
from fanfan.application.interactors.notifications.get_unread_count import (
    GetUnreadNotificationsCount,
    UnreadNotificationsCountOutput,
)
from fanfan.application.interactors.notifications.list_broadcasts import (
    ListBroadcasts,
    ListBroadcastsInput,
    ListBroadcastsOutput,
)
from fanfan.application.interactors.notifications.list_user_notifications import (
    ListUserNotificationOutput,
    ListUserNotifications,
    ListUserNotificationsInput,
)
from fanfan.application.interactors.notifications.mark_all_read import MarkAllRead
from fanfan.application.interactors.notifications.mark_read import (
    MarkNotificationsRead,
    MarkNotificationsReadInput,
)
from fanfan.application.interactors.notifications.send_broadcast import (
    SendBroadcast,
    SendBroadcastInput,
    SendBroadcastOutput,
)
from fanfan.application.interactors.notifications.send_test_notification import (
    SendTestNotification,
)
from fanfan.core.vo.mailing import MailingId
from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.security import session_security

notifications_router = APIRouter(
    tags=["Notifications"],
    prefix="/notifications",
    dependencies=[session_security],
    responses=AUTH_RESPONSES,
)


@notifications_router.get(
    "/",
    summary="List user notifications",
    description="Returns a paginated list of notifications for the authenticated user.",
    responses={
        200: {
            "model": ListUserNotificationOutput,
            "description": "Notifications retrieved successfully.",
        },
    },
)
@inject
async def list_user_notifications(
    interactor: FromDishka[ListUserNotifications],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListUserNotificationOutput:
    data = ListUserNotificationsInput(pagination=Pagination(limit=limit, offset=offset))
    return await interactor(data)


@notifications_router.get(
    "/unread-count",
    summary="Count unread notifications",
    description=(
        "Returns the total number of unread notifications for the authenticated "
        "user, independent of any page size — the bell badge is driven by this."
    ),
    responses={
        200: {
            "model": UnreadNotificationsCountOutput,
            "description": "Unread count retrieved successfully.",
        },
    },
)
@inject
async def count_unread_notifications(
    interactor: FromDishka[GetUnreadNotificationsCount],
) -> UnreadNotificationsCountOutput:
    return await interactor()


@notifications_router.post(
    "/mark-all-read",
    status_code=204,
    summary="Mark all notifications as read",
    description="Marks all unread notifications for the authenticated user as read.",
    responses={
        204: {"description": "All notifications marked as read."},
    },
)
@inject
async def mark_all_notifications_read(
    interactor: FromDishka[MarkAllRead],
) -> None:
    await interactor()


@notifications_router.post(
    "/mark-read",
    status_code=204,
    summary="Mark specific notifications as read",
    description=(
        "Marks the given notifications as read for the authenticated user. Used "
        "when opening the notifications panel or page marks the visible items seen."
    ),
    responses={
        204: {"description": "Notifications marked as read."},
    },
)
@inject
async def mark_notifications_read(
    data: MarkNotificationsReadInput,
    interactor: FromDishka[MarkNotificationsRead],
) -> None:
    await interactor(data)


@notifications_router.post(
    "/test",
    status_code=204,
    summary="Send test notification",
    description=(
        "Creates a test notification for the authenticated user and sends it through "
        "all connected channels."
    ),
    responses={
        204: {"description": "Test notification created successfully."},
    },
)
@inject
async def send_test_notification(
    interactor: FromDishka[SendTestNotification],
) -> None:
    await interactor()


@notifications_router.post(
    "/broadcast",
    summary="Send broadcast notification",
    description="Creates a new mailing broadcast for specified user roles.",
    responses={
        200: {
            "model": SendBroadcastOutput,
            "description": "Broadcast initiated successfully.",
        },
    },
)
@inject
async def send_broadcast(
    data: SendBroadcastInput,
    interactor: FromDishka[SendBroadcast],
) -> SendBroadcastOutput:
    return await interactor(data)


@notifications_router.get(
    "/broadcast",
    summary="List broadcasts",
    description=(
        "Returns organizer broadcasts newest-first, paginated. Schedule-change "
        "fan-outs are excluded — only role-targeted broadcasts appear."
    ),
    responses={
        200: {
            "model": ListBroadcastsOutput,
            "description": "Broadcasts retrieved successfully.",
        },
    },
)
@inject
async def list_broadcasts(
    interactor: FromDishka[ListBroadcasts],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListBroadcastsOutput:
    data = ListBroadcastsInput(pagination=Pagination(limit=limit, offset=offset))
    return await interactor(data)


@notifications_router.post(
    "/broadcast/{mailing_id}/cancel",
    status_code=204,
    summary="Cancel a mailing",
    description=(
        "Cancels a mailing: marks it cancelled and deletes its still-undelivered "
        "notifications. Messages already delivered to a device cannot be recalled."
    ),
    responses={
        204: {"description": "Mailing cancellation requested."},
    },
)
@inject
async def cancel_mailing(
    mailing_id: Annotated[MailingId, Path(description="ID of the mailing to cancel.")],
    interactor: FromDishka[CancelMailing],
) -> None:
    await interactor(CancelMailingInput(mailing_id=mailing_id))
