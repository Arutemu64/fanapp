import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.auth.authorize_telegram import (
    AuthorizeTelegram,
    AuthorizeTelegramInput,
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
TELEGRAM_SUBJECT = "1234123412341234123"
TELEGRAM_USER_ID = 987654321


async def test_first_login_creates_a_visitor_account(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(AuthorizeTelegram)
    user_gateway = await dishka_request.get(UserGateway)
    session_store = await dishka_request.get(SessionStore)

    session_id = await interactor(
        AuthorizeTelegramInput(
            subject=TELEGRAM_SUBJECT, provider_user_id=TELEGRAM_USER_ID
        )
    )

    resolution = await session_store.resolve_session(session_id)
    user = await user_gateway.get_by_id(resolution.user_id)
    assert user is not None
    assert user.role is UserRole.VISITOR
    # Telegram gives us no email, so the account starts without one — the unlink
    # guard (TelegramCannotBeUnlinkedWithoutEmail) depends on that staying true.
    assert user.email is None


async def test_first_login_stores_subject_and_notification_address(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(AuthorizeTelegram)
    social_identity_gateway = await dishka_request.get(SocialIdentityGateway)
    session_store = await dishka_request.get(SessionStore)

    session_id = await interactor(
        AuthorizeTelegramInput(
            subject=TELEGRAM_SUBJECT, provider_user_id=TELEGRAM_USER_ID
        )
    )

    resolution = await session_store.resolve_session(session_id)
    identity = await social_identity_gateway.get_by_provider(
        resolution.user_id, SocialProvider.TELEGRAM
    )
    assert identity is not None
    # The subject is the identity; the Bot API id is only the delivery address.
    assert identity.subject == TELEGRAM_SUBJECT
    assert identity.provider_user_id == TELEGRAM_USER_ID

    # The subject is what the next login looks the user up by.
    found = await social_identity_gateway.get_by_subject(
        provider=SocialProvider.TELEGRAM, subject=TELEGRAM_SUBJECT
    )
    assert found is not None
    assert found.user_id == resolution.user_id


async def test_returning_login_reuses_the_same_account(
    dishka_request: AsyncContainer,
):
    # The callback is unauthenticated and runs on every login, so a second visit
    # must resolve to the existing account rather than quietly creating a new one.
    interactor = await dishka_request.get(AuthorizeTelegram)
    session_store = await dishka_request.get(SessionStore)

    first_session = await interactor(
        AuthorizeTelegramInput(
            subject=TELEGRAM_SUBJECT, provider_user_id=TELEGRAM_USER_ID
        )
    )
    second_session = await interactor(
        AuthorizeTelegramInput(
            subject=TELEGRAM_SUBJECT, provider_user_id=TELEGRAM_USER_ID
        )
    )

    assert first_session != second_session
    first = await session_store.resolve_session(first_session)
    second = await session_store.resolve_session(second_session)
    assert first.user_id == second.user_id


async def test_different_subjects_get_different_users(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(AuthorizeTelegram)
    session_store = await dishka_request.get(SessionStore)

    one = await interactor(
        AuthorizeTelegramInput(
            subject=TELEGRAM_SUBJECT, provider_user_id=TELEGRAM_USER_ID
        )
    )
    two = await interactor(
        AuthorizeTelegramInput(
            subject=f"{TELEGRAM_SUBJECT}9", provider_user_id=TELEGRAM_USER_ID + 1
        )
    )

    first = await session_store.resolve_session(one)
    second = await session_store.resolve_session(two)
    assert first.user_id != second.user_id


async def test_login_backfills_a_missing_notification_address(
    dishka_request: AsyncContainer,
):
    # A token carrying only `openid` has no Bot API id, which would leave the
    # account unreachable over Telegram forever. The next login that does carry
    # one has to heal it — nothing else ever writes this column.
    interactor = await dishka_request.get(AuthorizeTelegram)
    social_identity_gateway = await dishka_request.get(SocialIdentityGateway)
    session_store = await dishka_request.get(SessionStore)

    await interactor(
        AuthorizeTelegramInput(subject=TELEGRAM_SUBJECT, provider_user_id=None)
    )
    session_id = await interactor(
        AuthorizeTelegramInput(
            subject=TELEGRAM_SUBJECT, provider_user_id=TELEGRAM_USER_ID
        )
    )

    resolution = await session_store.resolve_session(session_id)
    identity = await social_identity_gateway.get_by_provider(
        resolution.user_id, SocialProvider.TELEGRAM
    )
    assert identity is not None
    assert identity.provider_user_id == TELEGRAM_USER_ID
