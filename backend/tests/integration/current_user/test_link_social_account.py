from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.current_user.link_social_account import (
    LinkSocialAccount,
    LinkSocialAccountInput,
)
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.users import (
    LinkInitiatorMismatch,
    SocialAccountLinkedToAnotherUser,
    UserAlreadyHasProviderLinked,
)
from fanfan.core.models.user import User
from fanfan.core.vo.social_identity import SocialProvider
from fanfan.core.vo.user import Username, UserRole, generate_user_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]

SUBJECT = "1234123412341234123"
PROVIDER_USER_ID = 987654321


async def _user(
    user_gateway: UserGateway,
    uow: UnitOfWork,
    *,
    username: str,
) -> User:
    user = User(
        id=generate_user_id(),
        username=Username(username),
        email=None,
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_gateway.add(user)
    await uow.commit()
    return user


async def test_linking_stores_subject_and_notification_address(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(LinkSocialAccount)
    user_gateway = await dishka_request.get(UserGateway)
    social_identity_gateway = await dishka_request.get(SocialIdentityGateway)
    user = await _user(user_gateway, uow, username="linker")
    login(user)

    await interactor(
        LinkSocialAccountInput(
            provider=SocialProvider.TELEGRAM,
            subject=SUBJECT,
            provider_user_id=PROVIDER_USER_ID,
            initiator_user_id=user.id,
        )
    )

    identity = await social_identity_gateway.get_by_provider(
        user.id, SocialProvider.TELEGRAM
    )
    assert identity is not None
    assert identity.subject == SUBJECT
    assert identity.provider_user_id == PROVIDER_USER_ID


# The security property the merged callback rests on: the flow records who
# started it, and finishing it while signed in as somebody else must refuse
# rather than attach the external account to whoever holds the session now.
async def test_a_session_change_mid_flow_refuses_the_link(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(LinkSocialAccount)
    user_gateway = await dishka_request.get(UserGateway)
    social_identity_gateway = await dishka_request.get(SocialIdentityGateway)
    initiator = await _user(user_gateway, uow, username="initiator")
    hijacker = await _user(user_gateway, uow, username="hijacker")
    login(hijacker)

    with pytest.raises(LinkInitiatorMismatch):
        await interactor(
            LinkSocialAccountInput(
                provider=SocialProvider.TELEGRAM,
                subject=SUBJECT,
                provider_user_id=PROVIDER_USER_ID,
                initiator_user_id=initiator.id,
            )
        )

    # Neither account gets the identity — not the one that asked, and above all
    # not the one that happened to be signed in.
    assert (
        await social_identity_gateway.get_by_provider(
            hijacker.id, SocialProvider.TELEGRAM
        )
        is None
    )
    assert (
        await social_identity_gateway.get_by_provider(
            initiator.id, SocialProvider.TELEGRAM
        )
        is None
    )


async def test_relinking_the_same_account_is_a_no_op(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    login: Callable[[User], None],
):
    # Double-tapping "connect" must not raise at the user — they already have
    # exactly what they asked for.
    interactor = await dishka_request.get(LinkSocialAccount)
    user_gateway = await dishka_request.get(UserGateway)
    user = await _user(user_gateway, uow, username="repeater")
    login(user)
    data = LinkSocialAccountInput(
        provider=SocialProvider.TELEGRAM,
        subject=SUBJECT,
        provider_user_id=PROVIDER_USER_ID,
        initiator_user_id=user.id,
    )

    await interactor(data)
    await interactor(data)


async def test_linking_a_second_account_of_the_same_provider_is_rejected(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(LinkSocialAccount)
    user_gateway = await dishka_request.get(UserGateway)
    user = await _user(user_gateway, uow, username="two_telegrams")
    login(user)

    await interactor(
        LinkSocialAccountInput(
            provider=SocialProvider.TELEGRAM,
            subject=SUBJECT,
            provider_user_id=PROVIDER_USER_ID,
            initiator_user_id=user.id,
        )
    )

    with pytest.raises(UserAlreadyHasProviderLinked):
        await interactor(
            LinkSocialAccountInput(
                provider=SocialProvider.TELEGRAM,
                subject=f"{SUBJECT}9",
                provider_user_id=PROVIDER_USER_ID + 1,
                initiator_user_id=user.id,
            )
        )


async def test_an_account_owned_by_another_user_is_rejected(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(LinkSocialAccount)
    user_gateway = await dishka_request.get(UserGateway)
    owner = await _user(user_gateway, uow, username="owner")
    newcomer = await _user(user_gateway, uow, username="newcomer")

    login(owner)
    await interactor(
        LinkSocialAccountInput(
            provider=SocialProvider.TELEGRAM,
            subject=SUBJECT,
            provider_user_id=PROVIDER_USER_ID,
            initiator_user_id=owner.id,
        )
    )

    login(newcomer)
    with pytest.raises(SocialAccountLinkedToAnotherUser):
        await interactor(
            LinkSocialAccountInput(
                provider=SocialProvider.TELEGRAM,
                subject=SUBJECT,
                provider_user_id=PROVIDER_USER_ID,
                initiator_user_id=newcomer.id,
            )
        )


async def test_two_providers_coexist_on_one_user(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    login: Callable[[User], None],
):
    # `(user_id, provider)` is unique, so one account may hold both a Telegram and
    # a VK identity at once — the two links must not collide.
    interactor = await dishka_request.get(LinkSocialAccount)
    user_gateway = await dishka_request.get(UserGateway)
    social_identity_gateway = await dishka_request.get(SocialIdentityGateway)
    user = await _user(user_gateway, uow, username="both_providers")
    login(user)

    await interactor(
        LinkSocialAccountInput(
            provider=SocialProvider.TELEGRAM,
            subject=SUBJECT,
            provider_user_id=PROVIDER_USER_ID,
            initiator_user_id=user.id,
        )
    )
    await interactor(
        LinkSocialAccountInput(
            provider=SocialProvider.VK,
            subject=f"{SUBJECT}9",
            provider_user_id=PROVIDER_USER_ID + 1,
            initiator_user_id=user.id,
        )
    )

    assert (
        await social_identity_gateway.get_by_provider(user.id, SocialProvider.TELEGRAM)
        is not None
    )
    assert (
        await social_identity_gateway.get_by_provider(user.id, SocialProvider.VK)
        is not None
    )
