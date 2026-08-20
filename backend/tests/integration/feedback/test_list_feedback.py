from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.page import Pagination
from fanfan.application.interactors.feedback.list_feedback import (
    ListFeedback,
    ListFeedbackInput,
)
from fanfan.application.ports.gateways.feedback import FeedbackGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.feedback import Feedback
from fanfan.core.models.user import User
from fanfan.core.vo.feedback import generate_feedback_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _add_feedback(
    dishka_request: AsyncContainer, author: User, text: str
) -> None:
    feedback_gateway = await dishka_request.get(FeedbackGateway)
    uow = await dishka_request.get(UnitOfWork)
    await feedback_gateway.add(
        Feedback(id=generate_feedback_id(), user_id=author.id, text=text)
    )
    await uow.commit()
    # Newest-first order is deterministic to assert via the id (uuid7) tiebreaker:
    # the test runs in one wrapping transaction, so created_at (server-side
    # func.now(), the transaction clock) is identical across these rows, and the
    # later-generated id sorts first under the gateway's id.desc() secondary sort.


async def test_list_feedback_returns_newest_first_with_author(
    dishka_request: AsyncContainer,
    feedback_reader: User,
    visitor: User,
    login: Callable[[User], None],
):
    await _add_feedback(dishka_request, visitor, "Первый отзыв")
    await _add_feedback(dishka_request, visitor, "Второй отзыв")

    interactor = await dishka_request.get(ListFeedback)
    login(feedback_reader)

    result = await interactor(
        ListFeedbackInput(pagination=Pagination(limit=100, offset=0))
    )

    assert [item.text for item in result.feedback] == ["Второй отзыв", "Первый отзыв"]
    newest = result.feedback[0]
    assert newest.user.id == visitor.id
    assert newest.user.username == visitor.username


async def test_list_feedback_paginates(
    dishka_request: AsyncContainer,
    feedback_reader: User,
    visitor: User,
    login: Callable[[User], None],
):
    await _add_feedback(dishka_request, visitor, "Первый отзыв")
    await _add_feedback(dishka_request, visitor, "Второй отзыв")

    interactor = await dishka_request.get(ListFeedback)
    login(feedback_reader)

    first_page = await interactor(
        ListFeedbackInput(pagination=Pagination(limit=1, offset=0))
    )
    second_page = await interactor(
        ListFeedbackInput(pagination=Pagination(limit=1, offset=1))
    )

    assert [item.text for item in first_page.feedback] == ["Второй отзыв"]
    assert [item.text for item in second_page.feedback] == ["Первый отзыв"]


async def test_list_feedback_denied_without_permission(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(ListFeedback)
    login(visitor)

    with pytest.raises(AccessDenied):
        await interactor(ListFeedbackInput(pagination=Pagination(limit=100, offset=0)))
