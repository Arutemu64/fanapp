from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.current_user.unlink_social_account import (
    UnlinkSocialAccount,
    UnlinkSocialAccountInput,
)
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.users import CannotRemoveLastSignInMethod
from fanfan.core.models.social_identity import SocialIdentity
from fanfan.core.models.user import User
from fanfan.core.vo.email import Email
from fanfan.core.vo.social_identity import SocialProvider, generate_social_identity_id
from fanfan.core.vo.user import Username, UserRole, generate_user_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]

TELEGRAM_SUBJECT = "1234123412341234123"
TELEGRAM_USER_ID = 987654321
VK_SUBJECT = "555000111"
VK_USER_ID = 555000111


async def _user(
    user_gateway: UserGateway,
    uow: UnitOfWork,
    *,
    username: str,
    email: Email | None = None,
) -> User:
    user = User(
        id=generate_user_id(),
        username=Username(username),
        email=email,
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_gateway.add(user)
    await uow.commit()
    return user


async def _link(
    gateway: SocialIdentityGateway,
    uow: UnitOfWork,
    *,
    user: User,
    provider: SocialProvider,
    subject: str,
    provider_user_id: int,
) -> None:
    await gateway.add(
        SocialIdentity(
            id=generate_social_identity_id(),
            user_id=user.id,
            provider=provider,
            subject=subject,
            provider_user_id=provider_user_id,
        )
    )
    await uow.commit()


async def test_unlinking_with_an_email_present_succeeds(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    login: Callable[[User], None],
):
    # Email drives password and email-code login, so removing the only social
    # identity still leaves a way in.
    interactor = await dishka_request.get(UnlinkSocialAccount)
    user_gateway = await dishka_request.get(UserGateway)
    gateway = await dishka_request.get(SocialIdentityGateway)
    user = await _user(
        user_gateway, uow, username="has_email", email=Email("user@example.com")
    )
    await _link(
        gateway,
        uow,
        user=user,
        provider=SocialProvider.TELEGRAM,
        subject=TELEGRAM_SUBJECT,
        provider_user_id=TELEGRAM_USER_ID,
    )
    login(user)

    await interactor(UnlinkSocialAccountInput(provider=SocialProvider.TELEGRAM))

    assert await gateway.get_by_provider(user.id, SocialProvider.TELEGRAM) is None


async def test_unlinking_the_last_sign_in_method_is_refused(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    login: Callable[[User], None],
):
    # No email and only one identity: removing it would lock the user out.
    interactor = await dishka_request.get(UnlinkSocialAccount)
    user_gateway = await dishka_request.get(UserGateway)
    gateway = await dishka_request.get(SocialIdentityGateway)
    user = await _user(user_gateway, uow, username="only_telegram")
    await _link(
        gateway,
        uow,
        user=user,
        provider=SocialProvider.TELEGRAM,
        subject=TELEGRAM_SUBJECT,
        provider_user_id=TELEGRAM_USER_ID,
    )
    login(user)

    with pytest.raises(CannotRemoveLastSignInMethod):
        await interactor(UnlinkSocialAccountInput(provider=SocialProvider.TELEGRAM))

    # The identity survives the refusal.
    assert await gateway.get_by_provider(user.id, SocialProvider.TELEGRAM) is not None


async def test_unlinking_one_of_two_providers_is_allowed_without_email(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    login: Callable[[User], None],
):
    # No email, but the other provider remains as a way in — this is exactly the
    # case the old per-provider "email required" rule got wrong.
    interactor = await dishka_request.get(UnlinkSocialAccount)
    user_gateway = await dishka_request.get(UserGateway)
    gateway = await dishka_request.get(SocialIdentityGateway)
    user = await _user(user_gateway, uow, username="both_no_email")
    await _link(
        gateway,
        uow,
        user=user,
        provider=SocialProvider.TELEGRAM,
        subject=TELEGRAM_SUBJECT,
        provider_user_id=TELEGRAM_USER_ID,
    )
    await _link(
        gateway,
        uow,
        user=user,
        provider=SocialProvider.VK,
        subject=VK_SUBJECT,
        provider_user_id=VK_USER_ID,
    )
    login(user)

    await interactor(UnlinkSocialAccountInput(provider=SocialProvider.TELEGRAM))

    assert await gateway.get_by_provider(user.id, SocialProvider.TELEGRAM) is None
    # VK stays, so the account is still reachable.
    assert await gateway.get_by_provider(user.id, SocialProvider.VK) is not None


async def test_unlinking_a_provider_that_is_not_linked_is_a_no_op(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    login: Callable[[User], None],
):
    # Delete stays idempotent so the profile can recover from stale UI safely,
    # and the guard never fires on an absent identity.
    interactor = await dishka_request.get(UnlinkSocialAccount)
    user_gateway = await dishka_request.get(UserGateway)
    user = await _user(user_gateway, uow, username="no_vk")
    login(user)

    await interactor(UnlinkSocialAccountInput(provider=SocialProvider.VK))
