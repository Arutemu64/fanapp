from urllib.parse import parse_qs
from uuid import uuid7

import httpx2
import pytest

from fanfan.adapters.vk import notifier as notifier_module
from fanfan.adapters.vk.config import VkConfig
from fanfan.adapters.vk.notifier import VkApiError, VkNotifier
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


class _VkTransport:
    """MockTransport handler standing in for the VK messages.send endpoint.

    VK answers with HTTP 200 and either a ``response`` or an ``error`` object;
    this replays a chosen error code (or a success) and records each request so
    tests can assert on the posted form body. The notifier opens its own client,
    so a fixture swaps httpx2.AsyncClient for one wired to this transport.
    """

    def __init__(self, *, error_code: int | None = None) -> None:
        self._error_code = error_code
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        if self._error_code is not None:
            body = {"error": {"error_code": self._error_code, "error_msg": "boom"}}
        else:
            body = {"response": {"message_id": 1}}
        return httpx2.Response(200, json=body)

    @property
    def form_bodies(self) -> list[dict[str, str]]:
        # httpx sends the notifier's `data=` dict as a urlencoded form body.
        return [
            {key: values[0] for key, values in parse_qs(req.content.decode()).items()}
            for req in self.requests
        ]


@pytest.fixture
def install_transport(monkeypatch: pytest.MonkeyPatch):
    """Route the client the notifier opens internally through a MockTransport."""
    real_client = httpx2.AsyncClient

    def _install(transport: _VkTransport) -> None:
        def _factory(**_kwargs: object) -> httpx2.AsyncClient:
            return real_client(transport=httpx2.MockTransport(transport))

        monkeypatch.setattr(notifier_module.httpx2, "AsyncClient", _factory)

    return _install


def _vk_config() -> VkConfig:
    return VkConfig(
        client_id="app",
        client_secret="app-secret",  # type: ignore[arg-type]
        group_token="group-token",  # type: ignore[arg-type]
    )


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
) -> VkNotifier:
    return VkNotifier(
        config=_vk_config(),
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


async def test_sends_plain_text_to_linked_user(install_transport) -> None:
    transport = _VkTransport()
    install_transport(transport)
    user = _make_user()
    notifier = _notifier(user=user, identity=_identity_for(user))

    await notifier.send_notification(_make_notification(user.id))

    assert len(transport.form_bodies) == 1
    sent = transport.form_bodies[0]
    assert sent["peer_id"] == str(VK_USER_ID)
    # The group token and pinned API version travel in the POST body.
    assert sent["access_token"] == "group-token"
    assert sent["v"] == "5.199"
    # random_id 0 keeps VK from deduplicating distinct notifications.
    assert sent["random_id"] == "0"
    # The stored HTML body is flattened to plain text for VK.
    assert "<b>" not in sent["message"]
    assert "уведомления" in sent["message"]
    # The deep-link is appended as a bare, auto-linked URL.
    assert "https://app.example/schedule" in sent["message"]


async def test_opted_out_user_is_unreachable(install_transport) -> None:
    transport = _VkTransport()
    install_transport(transport)
    user = _make_user(receive_vk=False)
    notifier = _notifier(user=user, identity=_identity_for(user))

    with pytest.raises(UserNotReachable):
        await notifier.send_notification(_make_notification(user.id))
    # Short-circuits before touching the API.
    assert transport.requests == []


async def test_unlinked_user_is_unreachable(install_transport) -> None:
    transport = _VkTransport()
    install_transport(transport)
    user = _make_user()
    notifier = _notifier(user=user, identity=None)

    with pytest.raises(UserNotReachable):
        await notifier.send_notification(_make_notification(user.id))
    assert transport.requests == []


async def test_messages_not_allowed_is_unreachable(install_transport) -> None:
    # 901: the user never allowed the group to message them.
    install_transport(_VkTransport(error_code=901))
    user = _make_user()
    notifier = _notifier(user=user, identity=_identity_for(user))

    with pytest.raises(UserNotReachable):
        await notifier.send_notification(_make_notification(user.id))


async def test_flood_control_asks_to_retry(install_transport) -> None:
    # 6: too many requests — a transient condition worth retrying.
    install_transport(_VkTransport(error_code=6))
    user = _make_user()
    notifier = _notifier(user=user, identity=_identity_for(user))

    with pytest.raises(NotificationRetryAfter):
        await notifier.send_notification(_make_notification(user.id))


async def test_invalid_token_is_unreachable(install_transport) -> None:
    # 5: authorization failed — a channel misconfiguration, dropped per-message.
    install_transport(_VkTransport(error_code=5))
    user = _make_user()
    notifier = _notifier(user=user, identity=_identity_for(user))

    with pytest.raises(UserNotReachable):
        await notifier.send_notification(_make_notification(user.id))


async def test_unknown_error_propagates(install_transport) -> None:
    install_transport(_VkTransport(error_code=100500))
    user = _make_user()
    notifier = _notifier(user=user, identity=_identity_for(user))

    with pytest.raises(VkApiError):
        await notifier.send_notification(_make_notification(user.id))
