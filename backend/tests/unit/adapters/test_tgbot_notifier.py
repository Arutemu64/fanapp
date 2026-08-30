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


def _identity(*, provider_user_id: int | None = TG_USER_ID) -> SocialIdentity:
    return SocialIdentity(
        id=generate_social_identity_id(),
        user_id=USER_ID,
        provider=SocialProvider.TELEGRAM,
        subject=str(TG_USER_ID),
        provider_user_id=provider_user_id,
    )


def _web_config() -> WebConfig:
    return WebConfig(
        host="localhost",
        port=8000,
        public_url="https://app.example",  # type: ignore[arg-type]
        secret_key="secret",  # type: ignore[arg-type]
    )


class _RecordingBot:
    """Stands in for aiogram's Bot, recording each send and optionally raising."""

    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.calls: list[dict] = []

    async def send_message(self, **kwargs: object) -> None:
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error


class _StubSocialIdentityGateway:
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
        bot=bot,  # type: ignore[arg-type]
        social_identity_gateway=_StubSocialIdentityGateway(identity),  # type: ignore[arg-type]
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


async def test_identity_without_bot_id_is_unreachable() -> None:
    # An identity created from an `openid`-only token carries no Bot API id.
    bot = _RecordingBot()
    notifier = _notifier(identity=_identity(provider_user_id=None), bot=bot)

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
