import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.auth.authorize_social_login import (
    AuthorizeSocialLogin,
    AuthorizeSocialLoginInput,
)
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.session_store import SessionStore
from fanfan.core.vo.social_identity import SocialProvider
from fanfan.core.vo.user import UserRole

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]

# Telegram's own sample token pairs these two — deliberately different values, so
# a test that confused them would fail rather than pass by coincidence.
SUBJECT = "1234123412341234123"
PROVIDER_USER_ID = 987654321


def _input(**overrides: object) -> AuthorizeSocialLoginInput:
    data: dict[str, object] = {
        "provider": SocialProvider.TELEGRAM,
        "subject": SUBJECT,
        "provider_user_id": PROVIDER_USER_ID,
    }
    data.update(overrides)
    return AuthorizeSocialLoginInput(**data)  # type: ignore[arg-type]


async def test_first_login_creates_a_visitor_account(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(AuthorizeSocialLogin)
    user_gateway = await dishka_request.get(UserGateway)
    session_store = await dishka_request.get(SessionStore)

    session_id = await interactor(_input())

    resolution = await session_store.resolve_session(session_id)
    user = await user_gateway.get_by_id(resolution.user_id)
    assert user is not None
    assert user.role is UserRole.VISITOR
    # A social provider gives us no email, so the account starts without one — the
    # unlink guard (CannotRemoveLastSignInMethod) depends on that staying true.
    assert user.email is None


async def test_first_login_stores_subject_and_notification_address(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(AuthorizeSocialLogin)
    social_identity_gateway = await dishka_request.get(SocialIdentityGateway)
    session_store = await dishka_request.get(SessionStore)

    session_id = await interactor(_input())

    resolution = await session_store.resolve_session(session_id)
    identity = await social_identity_gateway.get_by_provider(
        resolution.user_id, SocialProvider.TELEGRAM
    )
    assert identity is not None
    # The subject is the identity; the native id is only the delivery address.
    assert identity.subject == SUBJECT
    assert identity.provider_user_id == PROVIDER_USER_ID

    # The subject is what the next login looks the user up by.
    found = await social_identity_gateway.get_by_subject(
        provider=SocialProvider.TELEGRAM, subject=SUBJECT
    )
    assert found is not None
    assert found.user_id == resolution.user_id


async def test_returning_login_reuses_the_same_account(
    dishka_request: AsyncContainer,
):
    # The callback is unauthenticated and runs on every login, so a second visit
    # must resolve to the existing account rather than quietly creating a new one.
    interactor = await dishka_request.get(AuthorizeSocialLogin)
    session_store = await dishka_request.get(SessionStore)

    first_session = await interactor(_input())
    second_session = await interactor(_input())

    assert first_session != second_session
    first = await session_store.resolve_session(first_session)
    second = await session_store.resolve_session(second_session)
    assert first.user_id == second.user_id


async def test_different_subjects_get_different_users(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(AuthorizeSocialLogin)
    session_store = await dishka_request.get(SessionStore)

    one = await interactor(_input())
    two = await interactor(
        _input(subject=f"{SUBJECT}9", provider_user_id=PROVIDER_USER_ID + 1)
    )

    first = await session_store.resolve_session(one)
    second = await session_store.resolve_session(two)
    assert first.user_id != second.user_id


async def test_same_subject_on_different_providers_is_two_identities(
    dishka_request: AsyncContainer,
):
    # `(provider, subject)` is the identity key: the same subject string arriving
    # from a different provider is a different account, never a collision.
    interactor = await dishka_request.get(AuthorizeSocialLogin)
    session_store = await dishka_request.get(SessionStore)

    telegram = await interactor(_input(provider=SocialProvider.TELEGRAM))
    vk = await interactor(_input(provider=SocialProvider.VK))

    first = await session_store.resolve_session(telegram)
    second = await session_store.resolve_session(vk)
    assert first.user_id != second.user_id
