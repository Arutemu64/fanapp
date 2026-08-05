from uuid import uuid7

import pytest
from vkbottle import VKAPIError

from fanfan.adapters.vk.notifier import VkNotifier
from fanfan.core.exceptions.notifications import (
    NotificationRetryAfter,
    UserNotReachable,
)
from fanfan.core.models.notification import Notification
from fanfan.core.models.social_identity import SocialIdentity
from fanfan.core.models.user import User, UserSettings
from fanfan.core.vo.notification import (
    NotificationType,
    generate_notification_id,
)
from fanfan.core.vo.social_identity import (
    SocialProvider,
    generate_social_identity_id,
)
from fanfan.core.vo.user import UserId, Username, UserRole
from fanfan.presentation.web.config import WebConfig

VK_USER_ID = 555


def _make_user(*, receive_vk: bool = True) -> User:
    return User(
        id=UserId(uuid7()),
        username=Username("tester"),
        hashed_password=None,
        role=UserRole.VISITOR,
        settings=UserSettings(receive_vk_notifications=receive_vk),
    )


def _make_notification(user_id: UserId) -> Notification:
    return Notification(
        id=generate_notification_id(),
        user_id=user_id,
        title="Внимание",
        body="Тело <b>уведомления</b>",
        type=NotificationType.DEFAULT,
        path="/schedule",
        mailing_id=None,
        seen_at=None,
    )


class _StubUserGateway:
    def __init__(self, user: User | None) -> None:
        self._user = user

    async def get_by_id(
        self,
        user_id: UserId,  # noqa: ARG002  # part of the port contract
    ) -> User | None:
        return self._user


class _StubSocialIdentityGateway:
    def __init__(self, identity: SocialIdentity | None) -> None:
        self._identity = identity

    async def get_by_provider(
        self,
        user_id: UserId,  # noqa: ARG002  # part of the port contract
        provider: SocialProvider,  # noqa: ARG002  # part of the port contract
    ) -> SocialIdentity | None:
        return self._identity


class _StubMessages:
    """Stands in for vkbottle's `api.messages`, raising a preset error."""

    def __init__(self, error: VKAPIError | None) -> None:
        self._error = error
        self.calls: list[dict] = []

    async def send(self, **kwargs: object) -> None:
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error


class _StubApi:
    def __init__(self, error: VKAPIError | None = None) -> None:
        self.messages = _StubMessages(error)


def _web_config() -> WebConfig:
    return WebConfig(
        host="localhost",
        port=8000,
        public_url="https://app.example",  # type: ignore[arg-type]
        secret_key="secret",  # type: ignore[arg-type]
    )


def _notifier(
    *,
    user: User | None,
    identity: SocialIdentity | None,
    api: _StubApi,
) -> VkNotifier:
    return VkNotifier(
        api=api,  # type: ignore[arg-type]
        user_gateway=_StubUserGateway(user),  # type: ignore[arg-type]
        social_identity_gateway=_StubSocialIdentityGateway(identity),  # type: ignore[arg-type]
        web_config=_web_config(),
    )


def _identity_for(user: User) -> SocialIdentity:
    return SocialIdentity(
        id=generate_social_identity_id(),
        user_id=user.id,
        provider=SocialProvider.VK,
        subject=str(VK_USER_ID),
        provider_user_id=VK_USER_ID,
    )


async def test_sends_plain_text_to_linked_user() -> None:
    user = _make_user()
    api = _StubApi()
    notifier = _notifier(user=user, identity=_identity_for(user), api=api)

    await notifier.send_notification(_make_notification(user.id))

    assert len(api.messages.calls) == 1
    sent = api.messages.calls[0]
    assert sent["peer_id"] == VK_USER_ID
    # The stored HTML body is flattened to plain text for VK.
    assert "<b>" not in sent["message"]
    assert "уведомления" in sent["message"]
    # The deep-link is appended as a bare, auto-linked URL.
    assert "https://app.example/schedule" in sent["message"]


async def test_opted_out_user_is_unreachable() -> None:
    user = _make_user(receive_vk=False)
    api = _StubApi()
    notifier = _notifier(user=user, identity=_identity_for(user), api=api)

    with pytest.raises(UserNotReachable):
        await notifier.send_notification(_make_notification(user.id))
    # Short-circuits before touching the API.
    assert api.messages.calls == []


async def test_unlinked_user_is_unreachable() -> None:
    user = _make_user()
    api = _StubApi()
    notifier = _notifier(user=user, identity=None, api=api)

    with pytest.raises(UserNotReachable):
        await notifier.send_notification(_make_notification(user.id))
    assert api.messages.calls == []


async def test_messages_not_allowed_is_unreachable() -> None:
    user = _make_user()
    # 901: the user never allowed the group to message them.
    api = _StubApi(VKAPIError[901](error_msg="not allowed"))
    notifier = _notifier(user=user, identity=_identity_for(user), api=api)

    with pytest.raises(UserNotReachable):
        await notifier.send_notification(_make_notification(user.id))


async def test_flood_control_asks_to_retry() -> None:
    user = _make_user()
    # 6: too many requests — a transient condition worth retrying.
    api = _StubApi(VKAPIError[6](error_msg="too many requests"))
    notifier = _notifier(user=user, identity=_identity_for(user), api=api)

    with pytest.raises(NotificationRetryAfter):
        await notifier.send_notification(_make_notification(user.id))


async def test_invalid_token_is_unreachable() -> None:
    user = _make_user()
    # 5: authorization failed — a channel misconfiguration, dropped per-message.
    api = _StubApi(VKAPIError[5](error_msg="auth failed"))
    notifier = _notifier(user=user, identity=_identity_for(user), api=api)

    with pytest.raises(UserNotReachable):
        await notifier.send_notification(_make_notification(user.id))


async def test_unknown_error_propagates() -> None:
    user = _make_user()
    api = _StubApi(VKAPIError[100500](error_msg="mystery"))
    notifier = _notifier(user=user, identity=_identity_for(user), api=api)

    with pytest.raises(VKAPIError):
        await notifier.send_notification(_make_notification(user.id))
