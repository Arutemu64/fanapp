from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.page import Pagination
from fanfan.application.interactors.notifications.list_user_notifications import (
    ListUserNotifications,
    ListUserNotificationsInput,
)
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.notification import Notification
from fanfan.core.models.user import User
from fanfan.core.vo.notification import (
    NotificationId,
    NotificationType,
    generate_notification_id,
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _add_notification(
    dishka_request: AsyncContainer, owner: User, body: str
) -> NotificationId:
    """Insert a notification and return its id.

    The test runs in one wrapping transaction, so created_at (server-side
    func.now(), the transaction clock) is identical across these rows; the
    later-generated id (uuid7 here) then decides order under the gateway's
    id.desc() tiebreaker — a regression guard for offset pages skipping rows.
    """
    notification_gateway = await dishka_request.get(NotificationGateway)
    uow = await dishka_request.get(UnitOfWork)
    notification = Notification(
        id=generate_notification_id(),
        user_id=owner.id,
        title="Заголовок",
        body=body,
        type=NotificationType.DEFAULT,
        path=None,
        mailing_id=None,
        seen_at=None,
    )
    await notification_gateway.add(notification)
    await uow.commit()
    return notification.id


async def test_list_user_notifications_newest_first_stable_under_created_at_tie(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    first = await _add_notification(dishka_request, visitor, "Первое")
    second = await _add_notification(dishka_request, visitor, "Второе")

    interactor = await dishka_request.get(ListUserNotifications)
    login(visitor)

    result = await interactor(
        ListUserNotificationsInput(pagination=Pagination(limit=100, offset=0))
    )

    assert [n.id for n in result.notifications] == [second, first]


async def test_list_user_notifications_paginates_without_skips(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    first = await _add_notification(dishka_request, visitor, "Первое")
    second = await _add_notification(dishka_request, visitor, "Второе")

    interactor = await dishka_request.get(ListUserNotifications)
    login(visitor)

    first_page = await interactor(
        ListUserNotificationsInput(pagination=Pagination(limit=1, offset=0))
    )
    second_page = await interactor(
        ListUserNotificationsInput(pagination=Pagination(limit=1, offset=1))
    )

    assert [n.id for n in first_page.notifications] == [second]
    assert [n.id for n in second_page.notifications] == [first]
