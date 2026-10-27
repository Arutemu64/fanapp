from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.page import CursorPagination
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


async def test_list_feedback_returns_newest_first_with_author(
    dishka_request: AsyncContainer,
    feedback_reader: User,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    await _add_feedback(dishka_request, visitor, "Первый отзыв")
    await _add_feedback(dishka_request, visitor, "Второй отзыв")

    interactor = await dishka_request.get(ListFeedback)
    login(feedback_reader)

    result = await interactor(ListFeedbackInput(pagination=CursorPagination(limit=100)))

    assert [item.text for item in result.feedback] == ["Второй отзыв", "Первый отзыв"]
    newest = result.feedback[0]
    assert newest.user.id == visitor.id
    assert newest.user.username == visitor.username


async def test_list_feedback_paginates(
    dishka_request: AsyncContainer,
    feedback_reader: User,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    await _add_feedback(dishka_request, visitor, "Первый отзыв")
    await _add_feedback(dishka_request, visitor, "Второй отзыв")

    interactor = await dishka_request.get(ListFeedback)
    login(feedback_reader)

    first_page = await interactor(
        ListFeedbackInput(pagination=CursorPagination(limit=1))
    )
    second_page = await interactor(
        ListFeedbackInput(
            pagination=CursorPagination.from_token(
                limit=1, cursor=first_page.next_cursor
            )
        )
    )

    assert [item.text for item in first_page.feedback] == ["Второй отзыв"]
    assert [item.text for item in second_page.feedback] == ["Первый отзыв"]
    assert first_page.next_cursor is not None
    assert second_page.next_cursor is None


async def test_list_feedback_denied_without_permission(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(ListFeedback)
    login(visitor)

    with pytest.raises(AccessDenied):
        await interactor(ListFeedbackInput(pagination=CursorPagination(limit=100)))
