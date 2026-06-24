# Replace with your generated VAPID keys

from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Query

from fanfan.application.dto.page import Pagination
from fanfan.application.interactors.notifications.list_user_notifications import (
    ListUserNotificationOutput,
    ListUserNotifications,
    ListUserNotificationsInput,
)
from fanfan.application.interactors.notifications.mark_all_read import MarkAllRead
from fanfan.application.interactors.notifications.send_broadcast import (
    SendBroadcast,
    SendBroadcastInput,
    SendBroadcastOutput,
)
from fanfan.application.interactors.notifications.send_test_notification import (
    SendTestNotification,
)
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
