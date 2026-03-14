# Replace with your generated VAPID keys

from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Query

from fanfan.application.notifications.list_user_notifications import (
    ListUserNotifications,
    ListUserNotificationsCommand,
    ListUserNotificationsResult,
)
from fanfan.application.notifications.mark_all_read import MarkAllRead
from fanfan.application.notifications.send_test_notification import (
    SendTestNotification,
)
from fanfan.core.dto.page import Pagination

notifications_router = APIRouter(tags=["Notifications"], prefix="/notifications")


@notifications_router.get(
    "/",
    summary="List user notifications",
    description="Returns a paginated list of notifications for the authenticated user.",
    responses={
        200: {
            "model": ListUserNotificationsResult,
            "description": "Notifications retrieved successfully.",
        },
    },
)
@inject
async def list_user_notifications(
    interactor: FromDishka[ListUserNotifications],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListUserNotificationsResult:
    data = ListUserNotificationsCommand(
        pagination=Pagination(limit=limit, offset=offset)
    )
    return await interactor(data)


@notifications_router.post(
    "/mark-all-read",
    summary="Mark all notifications as read",
    description="Marks all unread notifications for the authenticated user as read.",
    responses={
        200: {"description": "All notifications marked as read."},
    },
)
@inject
async def mark_all_notifications_read(
    interactor: FromDishka[MarkAllRead],
) -> None:
    await interactor()
    return


@notifications_router.post(
    "/test",
    summary="Send test notification",
    description=(
        "Creates a test notification for the authenticated user and sends it through "
        "all connected channels."
    ),
    responses={
        200: {"description": "Test notification created successfully."},
    },
)
@inject
async def send_test_notification(
    interactor: FromDishka[SendTestNotification],
) -> None:
    await interactor()
    return
