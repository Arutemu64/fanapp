from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.auth.confirm_email_code import (
    ConfirmEmailCode,
    ConfirmEmailCodeInput,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.token_registry import TokenRegistry
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.auth import InvalidOtpCode
from fanfan.core.models.user import User
from fanfan.core.vo.email import Email
from fanfan.core.vo.user import Username, UserRole, generate_user_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]

VALID_CODE = "123456"
WRONG_CODE = "000000"
CODE_TTL_SECONDS = 300


async def _make_user(
    user_gateway: UserGateway,
    uow: UnitOfWork,
    username: str,
    email: str | None,
) -> User:
    user = User(
        id=generate_user_id(),
        username=Username(username),
        email=Email(email) if email else None,
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_gateway.add(user)
    await uow.commit()
    return user


async def test_confirm_email_code_sets_the_confirmed_email(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(ConfirmEmailCode)
    user_gateway = await dishka_request.get(UserGateway)
    token_registry = await dishka_request.get(TokenRegistry)

    user = await _make_user(user_gateway, uow, "confirmer", email=None)
    login(user)
    await token_registry.issue_email_confirmation_code(
        user_id=user.id,
        email="target@example.com",
        code=VALID_CODE,
        ttl_seconds=CODE_TTL_SECONDS,
    )

    await interactor(ConfirmEmailCodeInput(code=VALID_CODE))

    reloaded = await user_gateway.get_by_id(user.id)
    assert reloaded is not None
    assert reloaded.email == Email("target@example.com")


async def test_confirm_email_code_wrong_code_raises_and_keeps_email(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(ConfirmEmailCode)
    user_gateway = await dishka_request.get(UserGateway)
    token_registry = await dishka_request.get(TokenRegistry)

    user = await _make_user(user_gateway, uow, "confirmer", email="old@example.com")
    login(user)
    await token_registry.issue_email_confirmation_code(
        user_id=user.id,
        email="target@example.com",
        code=VALID_CODE,
        ttl_seconds=CODE_TTL_SECONDS,
    )

    with pytest.raises(InvalidOtpCode):
        await interactor(ConfirmEmailCodeInput(code=WRONG_CODE))

    reloaded = await user_gateway.get_by_id(user.id)
    assert reloaded is not None
    assert reloaded.email == Email("old@example.com")


async def test_confirm_email_code_rejects_email_taken_by_another_user(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    login: Callable[[User], None],
):
    # The code is valid, but its target email already belongs to someone else,
    # so confirming it would collide — the interactor refuses it as invalid.
    interactor = await dishka_request.get(ConfirmEmailCode)
    user_gateway = await dishka_request.get(UserGateway)
    token_registry = await dishka_request.get(TokenRegistry)

    other = await _make_user(user_gateway, uow, "owner", email="taken@example.com")
    user = await _make_user(user_gateway, uow, "confirmer", email=None)
    login(user)
    await token_registry.issue_email_confirmation_code(
        user_id=user.id,
        email=other.email.value,
        code=VALID_CODE,
        ttl_seconds=CODE_TTL_SECONDS,
    )

    with pytest.raises(InvalidOtpCode):
        await interactor(ConfirmEmailCodeInput(code=VALID_CODE))

    reloaded = await user_gateway.get_by_id(user.id)
    assert reloaded is not None
    assert reloaded.email is None
