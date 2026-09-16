from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.page import Pagination
from fanfan.application.interactors.schedule_mgmt.list_schedule_changes import (
    ListScheduleChanges,
    ListScheduleChangesInput,
)
from fanfan.application.ports.gateways import ScheduleChangeGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.models.user import User
from fanfan.core.vo.schedule_change import ScheduleChangeId

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _add_change(dishka_request: AsyncContainer, author: User) -> ScheduleChangeId:
    """Insert a schedule change and return its id.

    The test runs in one wrapping transaction, so created_at (server-side
    func.now(), the transaction clock) is identical across these rows; the
    later-generated id (uuid7) then decides order under the gateway's
    id.desc() tiebreaker — a regression guard for offset pages skipping rows.
    """
    schedule_change_gateway = await dishka_request.get(ScheduleChangeGateway)
    uow = await dishka_request.get(UnitOfWork)
    change = ScheduleChange.set_as_current(
        changed_event_id=None,
        previous_event_id=None,
        mailing_id=None,
        user_id=author.id,
    )
    await schedule_change_gateway.add(change)
    await uow.commit()
    return change.id


async def test_list_schedule_changes_newest_first_stable_under_created_at_tie(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
):
    first = await _add_change(dishka_request, schedule_editor)
    second = await _add_change(dishka_request, schedule_editor)

    interactor = await dishka_request.get(ListScheduleChanges)
    login(schedule_editor)

    result = await interactor(
        ListScheduleChangesInput(pagination=Pagination(limit=100, offset=0))
    )

    assert [c.id for c in result.schedule_changes] == [second, first]


async def test_list_schedule_changes_paginates_without_skips(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
):
    first = await _add_change(dishka_request, schedule_editor)
    second = await _add_change(dishka_request, schedule_editor)

    interactor = await dishka_request.get(ListScheduleChanges)
    login(schedule_editor)

    first_page = await interactor(
        ListScheduleChangesInput(pagination=Pagination(limit=1, offset=0))
    )
    second_page = await interactor(
        ListScheduleChangesInput(pagination=Pagination(limit=1, offset=1))
    )

    assert [c.id for c in first_page.schedule_changes] == [second]
    assert [c.id for c in second_page.schedule_changes] == [first]


async def test_list_schedule_changes_denied_without_permission(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(ListScheduleChanges)
    login(visitor)

    with pytest.raises(AccessDenied):
        await interactor(
            ListScheduleChangesInput(pagination=Pagination(limit=100, offset=0))
        )
