from typing import Any
from uuid import uuid7

import pytest
from aiogram.enums import ParseMode
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
    TelegramUnauthorizedError,
)
from aiogram.methods import SendMessage

from fanfan.adapters.tgbot.notifier import TelegramNotifier
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
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


class _RecordingBot:
    """Stands in for aiogram's Bot, recording each send and optionally raising.

    Structural rather than a `Bot` subclass: `Bot.__init__` demands a real token
    and its `send_message` carries the full Bot API signature, which an override
    narrowing to `**kwargs` cannot satisfy. Hence the suppression at the call site.
    """

    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.calls: list[dict[str, Any]] = []

    async def send_message(self, **kwargs: object) -> None:
        self.calls.append(kwargs)
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


def _notifier(
    *, identity: SocialIdentity | None, bot: _RecordingBot
) -> TelegramNotifier:
    return TelegramNotifier(
        bot=bot,  # ty: ignore[invalid-argument-type]  # see _RecordingBot
        social_identity_gateway=_StubSocialIdentityGateway(identity),
        web_config=_web_config(),
    )


async def test_sends_html_with_escaped_title_and_deep_link_button() -> None:
    bot = _RecordingBot()
    notifier = _notifier(identity=_identity(), bot=bot)

    await notifier.send_notification(_notification(title="Кафе A&B"))

    assert len(bot.calls) == 1
    call = bot.calls[0]
    assert call["chat_id"] == TG_USER_ID
    assert call["parse_mode"] == ParseMode.HTML
    # The plain-text title is uppercased and HTML-escaped before wrapping in <b>;
    # the stored body (already a safe HTML subset) is passed through untouched.
    assert "КАФЕ A&amp;B" in call["text"]
    assert "Тело <b>уведомления</b>" in call["text"]
    # The deep-link button points at the in-app path on the public host.
    button = call["reply_markup"].inline_keyboard[0][0]
    assert button.url == "https://app.example/schedule"


async def test_unlinked_user_is_unreachable() -> None:
    bot = _RecordingBot()
    notifier = _notifier(identity=None, bot=bot)

    with pytest.raises(UserNotReachable):
        await notifier.send_notification(_notification())
    assert bot.calls == []


async def test_retry_after_maps_to_notification_retry_after() -> None:
    error = TelegramRetryAfter(
        method=SendMessage(chat_id=TG_USER_ID, text="x"),
        message="Too Many Requests: retry after 9",
        retry_after=9,
    )
    notifier = _notifier(identity=_identity(), bot=_RecordingBot(error=error))

    with pytest.raises(NotificationRetryAfter) as exc:
        await notifier.send_notification(_notification())
    assert exc.value.retry_after == 9


async def test_forbidden_is_unreachable() -> None:
    # The user blocked the bot or deleted their account.
    error = TelegramForbiddenError(
        method=SendMessage(chat_id=TG_USER_ID, text="x"),
        message="Forbidden: bot was blocked by the user",
    )
    notifier = _notifier(identity=_identity(), bot=_RecordingBot(error=error))

    with pytest.raises(UserNotReachable):
        await notifier.send_notification(_notification())


async def test_bad_request_is_unreachable() -> None:
    # A malformed request (e.g. unparseable message HTML) is dropped, not retried.
    error = TelegramBadRequest(
        method=SendMessage(chat_id=TG_USER_ID, text="x"),
        message="Bad Request: can't parse entities",
    )
    notifier = _notifier(identity=_identity(), bot=_RecordingBot(error=error))

    with pytest.raises(UserNotReachable):
        await notifier.send_notification(_notification())


async def test_unauthorized_token_is_channel_unavailable() -> None:
    # Invalid bot token — a channel-wide misconfiguration, not a per-user problem.
    error = TelegramUnauthorizedError(
        method=SendMessage(chat_id=TG_USER_ID, text="x"),
        message="Unauthorized",
    )
    notifier = _notifier(identity=_identity(), bot=_RecordingBot(error=error))

    with pytest.raises(NotificationChannelUnavailable):
        await notifier.send_notification(_notification())
