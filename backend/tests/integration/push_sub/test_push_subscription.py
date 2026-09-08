from collections.abc import Callable
from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.push_sub.check_push_subscription import (
    CheckPushSubscription,
    CheckPushSubscriptionInput,
)
from fanfan.application.interactors.push_sub.create_push_subscription import (
    CreatePushSubscription,
    CreatePushSubscriptionInput,
)
from fanfan.application.interactors.push_sub.delete_push_subscription import (
    DeletePushSubscription,
    DeletePushSubscriptionInput,
)
from fanfan.application.ports.gateways.push_subscriptions import (
    PushSubscriptionGateway,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.push_sub import (
    PushSubscriptionAlreadyExists,
    PushSubscriptionNotFound,
)
from fanfan.core.models.user import User
from fanfan.core.vo.user import UserId, Username, UserRole

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]

ENDPOINT = "https://push.example.test/endpoint/abc"


async def test_create_push_subscription_persists_endpoint(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(CreatePushSubscription)
    push_gateway = await dishka_request.get(PushSubscriptionGateway)
    login(visitor)

    await interactor(
        CreatePushSubscriptionInput(endpoint=ENDPOINT, p256dh="key", auth="auth")
    )

    saved = await push_gateway.get_by_endpoint(ENDPOINT)
    assert saved is not None
    assert saved.user_id == visitor.id
    assert saved.endpoint == ENDPOINT
    assert saved.p256dh == "key"
    assert saved.auth == "auth"


async def test_create_push_subscription_same_endpoint_twice_raises(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    """Document current behavior: registration is NOT idempotent.

    The endpoint column carries a unique constraint and CreatePushSubscription
    always inserts a fresh row without an upsert or existence check, so
    re-registering the same endpoint raises PushSubscriptionAlreadyExists rather
    than silently deduplicating.
    """
    interactor = await dishka_request.get(CreatePushSubscription)
    push_gateway = await dishka_request.get(PushSubscriptionGateway)
    login(visitor)

    await interactor(
        CreatePushSubscriptionInput(endpoint=ENDPOINT, p256dh="key", auth="auth")
    )

    with pytest.raises(PushSubscriptionAlreadyExists):
        await interactor(
            CreatePushSubscriptionInput(endpoint=ENDPOINT, p256dh="key2", auth="auth2")
        )

    await uow.rollback()
    # The first registration survives; the duplicate never landed.
    saved = await push_gateway.get_by_endpoint(ENDPOINT)
    assert saved is not None
    assert saved.p256dh == "key"


async def test_check_push_subscription_reports_presence(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    create = await dishka_request.get(CreatePushSubscription)
    check = await dishka_request.get(CheckPushSubscription)
    login(visitor)

    assert await check(CheckPushSubscriptionInput(endpoint=ENDPOINT)) is False

    await create(
        CreatePushSubscriptionInput(endpoint=ENDPOINT, p256dh="key", auth="auth")
    )

    assert await check(CheckPushSubscriptionInput(endpoint=ENDPOINT)) is True
    assert (
        await check(CheckPushSubscriptionInput(endpoint="https://other.test/x"))
        is False
    )


async def test_delete_push_subscription_removes_own_endpoint(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    create = await dishka_request.get(CreatePushSubscription)
    delete = await dishka_request.get(DeletePushSubscription)
    push_gateway = await dishka_request.get(PushSubscriptionGateway)
    login(visitor)

    await create(
        CreatePushSubscriptionInput(endpoint=ENDPOINT, p256dh="key", auth="auth")
    )

    await delete(DeletePushSubscriptionInput(endpoint=ENDPOINT))

    assert await push_gateway.get_by_endpoint(ENDPOINT) is None


async def test_delete_push_subscription_missing_raises_not_found(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    delete = await dishka_request.get(DeletePushSubscription)
    login(visitor)

    with pytest.raises(PushSubscriptionNotFound):
        await delete(DeletePushSubscriptionInput(endpoint="https://missing.test/x"))


async def test_delete_push_subscription_of_another_user_raises_access_denied(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    """Ownership guard: a user cannot delete another user's push endpoint."""
    create = await dishka_request.get(CreatePushSubscription)
    delete = await dishka_request.get(DeletePushSubscription)
    push_gateway = await dishka_request.get(PushSubscriptionGateway)
    user_gateway = await dishka_request.get(UserGateway)

    other_user = User(
        id=UserId(uuid7()),
        username=Username("other_pusher"),
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_gateway.add(other_user)
    await uow.commit()

    # visitor (owner) registers the endpoint.
    login(visitor)
    await create(
        CreatePushSubscriptionInput(endpoint=ENDPOINT, p256dh="key", auth="auth")
    )

    # other_user tries to delete the owner's endpoint.
    login(other_user)
    with pytest.raises(AccessDenied):
        await delete(DeletePushSubscriptionInput(endpoint=ENDPOINT))

    still_there = await push_gateway.get_by_endpoint(ENDPOINT)
    assert still_there is not None
    assert still_there.user_id == visitor.id
