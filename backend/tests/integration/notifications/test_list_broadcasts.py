from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.page import CursorPagination
from fanfan.application.interactors.notifications.list_broadcasts import (
    ListBroadcasts,
    ListBroadcastsInput,
)
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.mailing import Mailing
from fanfan.core.models.user import User
from fanfan.core.vo.user import UserRole
from tests.integration.conftest import make_broadcaster

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _add_broadcast(
    dishka_request: AsyncContainer, uow: UnitOfWork, author: User, body: str
) -> None:
    mailing_gateway = await dishka_request.get(MailingGateway)
    mailing = Mailing.create(by_user_id=author.id)
    mailing.queue_broadcast(body, [UserRole.VISITOR])
    await mailing_gateway.add(mailing)
    await uow.commit()
    # Newest-first order is asserted through the id (uuid7) tiebreaker: the test
    # runs in one wrapping transaction, so created_at is identical across rows.


async def test_list_broadcasts_pages_newest_first(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    broadcaster = await make_broadcaster(dishka_request, uow)
    await _add_broadcast(dishka_request, uow, broadcaster, "Первая рассылка")
    await _add_broadcast(dishka_request, uow, broadcaster, "Вторая рассылка")
    interactor = await dishka_request.get(ListBroadcasts)
    login(broadcaster)

    first_page = await interactor(
        ListBroadcastsInput(pagination=CursorPagination(limit=1))
    )
    second_page = await interactor(
        ListBroadcastsInput(
            pagination=CursorPagination.from_token(
                limit=1, cursor=first_page.next_cursor
            )
        )
    )

    assert [m.body for m in first_page.mailings] == ["Вторая рассылка"]
    assert [m.body for m in second_page.mailings] == ["Первая рассылка"]
    assert first_page.next_cursor is not None
    assert second_page.next_cursor is None


async def test_list_broadcasts_excludes_schedule_fan_outs(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    broadcaster = await make_broadcaster(dishka_request, uow)
    await _add_broadcast(dishka_request, uow, broadcaster, "Рассылка")
    # A schedule-change fan-out keeps roles NULL, which is what tells it apart
    # from a role-targeted broadcast.
    mailing_gateway = await dishka_request.get(MailingGateway)
    fan_out = Mailing.create(by_user_id=broadcaster.id)
    fan_out.record_summary("Изменения в расписании")
    await mailing_gateway.add(fan_out)
    await uow.commit()
    interactor = await dishka_request.get(ListBroadcasts)
    login(broadcaster)

    result = await interactor(
        ListBroadcastsInput(pagination=CursorPagination(limit=100))
    )

    assert [m.body for m in result.mailings] == ["Рассылка"]
    assert result.next_cursor is None


async def test_list_broadcasts_denied_without_permission(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(ListBroadcasts)
    login(visitor)

    with pytest.raises(AccessDenied):
        await interactor(ListBroadcastsInput(pagination=CursorPagination(limit=100)))
