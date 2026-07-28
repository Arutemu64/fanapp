import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.auth.authorize_telegram import (
    AuthorizeTelegram,
    AuthorizeTelegramInput,
)
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.session_store import SessionStore
from fanfan.core.vo.user import UserRole

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]

TELEGRAM_ID = 987654321
TELEGRAM_NAME = "John Doe"


async def test_first_login_creates_a_visitor_account(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(AuthorizeTelegram)
    user_gateway = await dishka_request.get(UserGateway)
    session_store = await dishka_request.get(SessionStore)

    session_id = await interactor(
        AuthorizeTelegramInput(user_id=TELEGRAM_ID, name=TELEGRAM_NAME)
    )

    resolution = await session_store.resolve_session(session_id)
    user = await user_gateway.get_by_id(resolution.user_id)
    assert user is not None
    assert user.role is UserRole.VISITOR
    # Telegram gives us no email, so the account starts without one — the unlink
    # guard (TelegramCannotBeUnlinkedWithoutEmail) depends on that staying true.
    assert user.email is None


async def test_first_login_links_the_telegram_identity(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(AuthorizeTelegram)
    user_gateway = await dishka_request.get(UserGateway)
    social_identity_gateway = await dishka_request.get(SocialIdentityGateway)
    session_store = await dishka_request.get(SessionStore)

    session_id = await interactor(
        AuthorizeTelegramInput(user_id=TELEGRAM_ID, name=TELEGRAM_NAME)
    )

    resolution = await session_store.resolve_session(session_id)
    identity = await social_identity_gateway.get_by_provider(
        resolution.user_id, "telegram"
    )
    assert identity is not None
    assert identity.provider_id == str(TELEGRAM_ID)

    # The identity is what the next login looks the user up by.
    found = await user_gateway.get_by_social_identity(
        provider_name="telegram", provider_account_id=str(TELEGRAM_ID)
    )
    assert found is not None
    assert found.id == resolution.user_id


async def test_returning_login_reuses_the_same_account(
    dishka_request: AsyncContainer,
):
    # The callback is unauthenticated and runs on every login, so a second visit
    # must resolve to the existing account rather than quietly creating a new one.
    interactor = await dishka_request.get(AuthorizeTelegram)
    session_store = await dishka_request.get(SessionStore)

    first_session = await interactor(
        AuthorizeTelegramInput(user_id=TELEGRAM_ID, name=TELEGRAM_NAME)
    )
    second_session = await interactor(
        AuthorizeTelegramInput(user_id=TELEGRAM_ID, name="Renamed On Telegram")
    )

    assert first_session != second_session
    first = await session_store.resolve_session(first_session)
    second = await session_store.resolve_session(second_session)
    assert first.user_id == second.user_id


async def test_different_telegram_accounts_get_different_users(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(AuthorizeTelegram)
    session_store = await dishka_request.get(SessionStore)

    one = await interactor(AuthorizeTelegramInput(user_id=TELEGRAM_ID, name="One"))
    two = await interactor(AuthorizeTelegramInput(user_id=TELEGRAM_ID + 1, name="Two"))

    first = await session_store.resolve_session(one)
    second = await session_store.resolve_session(two)
    assert first.user_id != second.user_id
