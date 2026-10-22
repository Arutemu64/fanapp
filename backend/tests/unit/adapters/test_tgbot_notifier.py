import json
from typing import Any
from uuid import uuid7

import httpx2
import pytest
from pydantic import SecretStr

from fanfan.adapters.tgbot.client import TelegramApiClient, TelegramApiError
from fanfan.adapters.tgbot.config import TelegramConfig
from fanfan.adapters.tgbot.notifier import TelegramNotifier, TelegramRateLimiter
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.notifications import (
    NotificationChannelUnavailable,
    NotificationRetryAfter,
    UserNotReachable,
)
from fanfan.core.models.notification import Notification
from fanfan.core.models.social_identity import SocialIdentity
from fanfan.core.vo.notification import NotificationType, generate_notification_id
from fanfan.core.vo.social_identity import SocialProvider, generate_social_identity_id
from fanfan.core.vo.user import UserId
from fanfan.presentation.web.config import WebConfig

pytestmark = pytest.mark.unit

USER_ID = UserId(uuid7())
TG_USER_ID = 777


def _notification(
    *, title: str = "Внимание", path: str | None = "/schedule"
) -> Notification:
    return Notification(
        id=generate_notification_id(),
        user_id=USER_ID,
        title=title,
        body="Тело <b>уведомления</b>",
        type=NotificationType.DEFAULT,
        path=path,
        mailing_id=None,
        seen_at=None,
    )


def _identity() -> SocialIdentity:
    return SocialIdentity(
        id=generate_social_identity_id(),
        user_id=USER_ID,
        provider=SocialProvider.TELEGRAM,
        subject=str(TG_USER_ID),
        provider_user_id=TG_USER_ID,
    )


def _web_config() -> WebConfig:
    return WebConfig(
        host="localhost",
        port=8000,
        public_url="https://app.example",
        secret_key="secret",
    )


class _RecordingClient(TelegramApiClient):
    """Records each send and optionally raises. Skips `super().__init__()`: the
    override replaces the only method that would use the HTTP client."""

    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.calls: list[dict[str, Any]] = []

    async def send_message(
        self, *, chat_id: int, text: str, reply_markup: dict[str, Any]
    ) -> None:
        self.calls.append(
            {"chat_id": chat_id, "text": text, "reply_markup": reply_markup}
        )
        if self._error is not None:
            raise self._error


class _StubSocialIdentityGateway(SocialIdentityGateway):
    def __init__(self, identity: SocialIdentity | None) -> None:
        self._identity = identity

    async def get_by_provider(
        self,
        user_id: UserId,  # noqa: ARG002  # part of the port contract
        provider: SocialProvider,  # noqa: ARG002  # part of the port contract
    ) -> SocialIdentity | None:
        return self._identity


class _StubUow(UnitOfWork):
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def _notifier(
    *,
    identity: SocialIdentity | None,
    client: _RecordingClient,
    uow: _StubUow | None = None,
) -> TelegramNotifier:
    return TelegramNotifier(
        client=client,
        social_identity_gateway=_StubSocialIdentityGateway(identity),
        uow=uow or _StubUow(),
        rate_limiter=TelegramRateLimiter(),
        web_config=_web_config(),
    )


async def test_ends_lookup_transaction_before_sending() -> None:
    uow = _StubUow()
    client = _RecordingClient()
    notifier = _notifier(identity=_identity(), client=client, uow=uow)

    await notifier.send_notification(_notification())

    # The send can take up to a minute; the pooled connection (and the
    # identity's row lock) must not be held through it.
    assert uow.commits == 1
    assert len(client.calls) == 1


async def test_sends_html_with_escaped_title_and_deep_link_button() -> None:
    client = _RecordingClient()
    notifier = _notifier(identity=_identity(), client=client)

    await notifier.send_notification(_notification(title="Кафе A&B"))

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["chat_id"] == TG_USER_ID
    # The plain-text title is uppercased and HTML-escaped before wrapping in <b>;
    # the stored body (already a safe HTML subset) is passed through untouched.
    assert "КАФЕ A&amp;B" in call["text"]
    assert "Тело <b>уведомления</b>" in call["text"]
    # The deep-link button points at the in-app path on the public host.
    button = call["reply_markup"]["inline_keyboard"][0][0]
    assert button["url"] == "https://app.example/schedule"


async def test_unlinked_user_is_unreachable() -> None:
    client = _RecordingClient()
    notifier = _notifier(identity=None, client=client)

    with pytest.raises(UserNotReachable):
        await notifier.send_notification(_notification())
    assert client.calls == []


async def test_retry_after_maps_to_notification_retry_after() -> None:
    error = TelegramApiError(
        status=429, description="Too Many Requests: retry after 9", retry_after=9
    )
    notifier = _notifier(identity=_identity(), client=_RecordingClient(error=error))

    with pytest.raises(NotificationRetryAfter) as exc:
        await notifier.send_notification(_notification())
    assert exc.value.retry_after == 9


async def test_forbidden_is_unreachable() -> None:
    # The user blocked the bot or deleted their account.
    error = TelegramApiError(
        status=403, description="Forbidden: bot was blocked by the user"
    )
    notifier = _notifier(identity=_identity(), client=_RecordingClient(error=error))

    with pytest.raises(UserNotReachable):
        await notifier.send_notification(_notification())


async def test_bad_request_is_unreachable() -> None:
    # A malformed request (e.g. unparseable message HTML) is dropped, not retried.
    error = TelegramApiError(
        status=400, description="Bad Request: can't parse entities"
    )
    notifier = _notifier(identity=_identity(), client=_RecordingClient(error=error))

    with pytest.raises(UserNotReachable):
        await notifier.send_notification(_notification())


async def test_unauthorized_token_is_channel_unavailable() -> None:
    # Invalid bot token — a channel-wide misconfiguration, not a per-user problem.
    error = TelegramApiError(status=401, description="Unauthorized")
    notifier = _notifier(identity=_identity(), client=_RecordingClient(error=error))

    with pytest.raises(NotificationChannelUnavailable):
        await notifier.send_notification(_notification())


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(
            TelegramApiError(status=502, description="Bad Gateway"), id="server_error"
        ),
        pytest.param(
            TelegramApiError(status=429, description="Too Many Requests"),
            id="rate_limited_without_retry_after",
        ),
    ],
)
async def test_transient_errors_propagate_for_redelivery(
    error: TelegramApiError,
) -> None:
    notifier = _notifier(identity=_identity(), client=_RecordingClient(error=error))

    with pytest.raises(TelegramApiError):
        await notifier.send_notification(_notification())


def _api_client(handler: httpx2.MockTransport) -> TelegramApiClient:
    return TelegramApiClient(
        client=httpx2.AsyncClient(transport=handler),
        config=TelegramConfig(
            token=SecretStr("123:abc"), client_id="id", client_secret=SecretStr("s")
        ),
    )


async def test_client_posts_json_to_the_token_path() -> None:
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(200, json={"ok": True, "result": {}})

    client = _api_client(httpx2.MockTransport(handler))
    await client.send_message(
        chat_id=7, text="hi", reply_markup={"inline_keyboard": []}
    )

    assert str(seen[0].url) == "https://api.telegram.org/bot123:abc/sendMessage"
    assert json.loads(seen[0].content) == {
        "chat_id": 7,
        "text": "hi",
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": []},
    }


async def test_client_reads_retry_after_from_a_429_body() -> None:
    body = {
        "ok": False,
        "error_code": 429,
        "description": "Too Many Requests: retry after 17",
        "parameters": {"retry_after": 17},
    }
    client = _api_client(
        httpx2.MockTransport(lambda _: httpx2.Response(429, json=body))
    )

    with pytest.raises(TelegramApiError) as exc:
        await client.send_message(chat_id=7, text="hi", reply_markup={})
    assert exc.value.status == 429
    assert exc.value.retry_after == 17


async def test_client_classifies_a_non_json_error_by_status() -> None:
    client = _api_client(
        httpx2.MockTransport(lambda _: httpx2.Response(502, text="<html>Bad Gateway"))
    )

    with pytest.raises(TelegramApiError) as exc:
        await client.send_message(chat_id=7, text="hi", reply_markup={})
    assert exc.value.status == 502
    assert exc.value.retry_after is None
