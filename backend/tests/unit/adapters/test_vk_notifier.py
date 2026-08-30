from urllib.parse import parse_qs
from uuid import uuid7

import httpx2
import pytest

from fanfan.adapters.vk.client import VkApiClient, VkApiError
from fanfan.adapters.vk.config import VkConfig
from fanfan.adapters.vk.notifier import VkNotifier
from fanfan.core.exceptions.notifications import (
    NotificationChannelUnavailable,
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


def _identity_for(user: User) -> SocialIdentity:
    return SocialIdentity(
        id=generate_social_identity_id(),
        user_id=user.id,
        provider=SocialProvider.VK,
        subject=str(VK_USER_ID),
        provider_user_id=VK_USER_ID,
    )


# --- VkApiClient: the HTTP call and VK's answer shape --------------------------


class _VkTransport:
    """MockTransport handler standing in for the VK messages.send endpoint.

    VK answers with HTTP 200 and either a ``response`` or an ``error`` object;
    this replays a chosen error code (or a success) and records each request so
    tests can assert on the posted form body.
    """

    def __init__(self, *, error_code: int | None = None) -> None:
        self._error_code = error_code
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        if self._error_code is not None:
            body: dict = {
                "error": {"error_code": self._error_code, "error_msg": "boom"}
            }
        else:
            # For a single peer_id, messages.send answers with the bare integer
            # message id; messages.delete answers with a truthy value we ignore.
            body = {"response": 1}
        return httpx2.Response(200, json=body)

    def form_body(self, index: int = 0) -> dict[str, str]:
        # httpx sends the client's `data=` dict as a urlencoded form body.
        content = self.requests[index].content.decode()
        return {key: values[0] for key, values in parse_qs(content).items()}


def _api_client(transport: _VkTransport) -> VkApiClient:
    http = httpx2.AsyncClient(transport=httpx2.MockTransport(transport))
    return VkApiClient(client=http, config=_vk_config())


async def test_client_posts_token_version_and_message() -> None:
    transport = _VkTransport()
    client = _api_client(transport)

    message_id = await client.send_message(peer_id=VK_USER_ID, message="привет")

    # For a single peer_id VK returns the bare integer id of the sent message.
    assert message_id == 1
    sent = transport.form_body()
    assert sent["peer_id"] == str(VK_USER_ID)
    assert sent["message"] == "привет"
    # The group token and pinned API version travel in the POST body.
    assert sent["access_token"] == "group-token"
    assert sent["v"] == "5.199"
    # random_id 0 keeps VK from deduplicating distinct notifications.
    assert sent["random_id"] == "0"


async def test_client_deletes_message_only_on_group_side() -> None:
    transport = _VkTransport()
    client = _api_client(transport)

    await client.delete_message(message_id=42)

    sent = transport.form_body()
    assert sent["message_ids"] == "42"
    # delete_for_all=0 removes the message from the group's side only, keeping it
    # in the user's inbox; the token and version still travel in the body.
    assert sent["delete_for_all"] == "0"
    assert sent["access_token"] == "group-token"
    assert sent["v"] == "5.199"


async def test_client_raises_vk_api_error_on_error_object() -> None:
    client = _api_client(_VkTransport(error_code=901))

    with pytest.raises(VkApiError) as exc:
        await client.send_message(peer_id=VK_USER_ID, message="hi")
    assert exc.value.code == 901


# --- VkNotifier: gateway guards and error-code translation --------------------


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


_SENT_MESSAGE_ID = 42


class _StubVkClient:
    """Stands in for VkApiClient, recording sends/deletes and optionally raising."""

    def __init__(
        self,
        error: VkApiError | None = None,
        *,
        delete_error: Exception | None = None,
    ) -> None:
        self._error = error
        self._delete_error = delete_error
        self.calls: list[dict] = []
        self.deleted: list[int] = []

    async def send_message(self, *, peer_id: int, message: str) -> int:
        self.calls.append({"peer_id": peer_id, "message": message})
        if self._error is not None:
            raise self._error
        return _SENT_MESSAGE_ID

    async def delete_message(self, *, message_id: int) -> None:
        self.deleted.append(message_id)
        if self._delete_error is not None:
            raise self._delete_error


def _notifier(
    *,
    user: User | None,
    identity: SocialIdentity | None,
    client: _StubVkClient,
) -> VkNotifier:
    return VkNotifier(
        client=client,  # type: ignore[arg-type]
        user_gateway=_StubUserGateway(user),  # type: ignore[arg-type]
        social_identity_gateway=_StubSocialIdentityGateway(identity),  # type: ignore[arg-type]
        web_config=_web_config(),
    )


async def test_sends_plain_text_to_linked_user() -> None:
    user = _make_user()
    client = _StubVkClient()
    notifier = _notifier(user=user, identity=_identity_for(user), client=client)

    await notifier.send_notification(_make_notification(user.id))

    assert len(client.calls) == 1
    sent = client.calls[0]
    assert sent["peer_id"] == VK_USER_ID
    # The stored HTML body is flattened to plain text for VK.
    assert "<b>" not in sent["message"]
    assert "уведомления" in sent["message"]
    # The deep-link is appended as a bare, auto-linked URL.
    assert "https://app.example/schedule" in sent["message"]
    # The group's own copy is deleted so it doesn't clutter the community inbox.
    assert client.deleted == [_SENT_MESSAGE_ID]


async def test_delete_failure_does_not_fail_delivery() -> None:
    user = _make_user()
    # The message was delivered; a failing cleanup must not surface as an error,
    # or the consumer would redeliver and re-send a duplicate to the user.
    client = _StubVkClient(delete_error=VkApiError(code=100500, message="boom"))
    notifier = _notifier(user=user, identity=_identity_for(user), client=client)

    await notifier.send_notification(_make_notification(user.id))

    assert len(client.calls) == 1
    assert client.deleted == [_SENT_MESSAGE_ID]


async def test_delete_skipped_when_send_fails() -> None:
    user = _make_user()
    client = _StubVkClient(VkApiError(code=901, message="not allowed"))
    notifier = _notifier(user=user, identity=_identity_for(user), client=client)

    with pytest.raises(UserNotReachable):
        await notifier.send_notification(_make_notification(user.id))
    # No message id to delete when the send itself never went through.
    assert client.deleted == []


async def test_opted_out_user_is_unreachable() -> None:
    user = _make_user(receive_vk=False)
    client = _StubVkClient()
    notifier = _notifier(user=user, identity=_identity_for(user), client=client)

    with pytest.raises(UserNotReachable):
        await notifier.send_notification(_make_notification(user.id))
    # Short-circuits before touching the API.
    assert client.calls == []


async def test_unlinked_user_is_unreachable() -> None:
    user = _make_user()
    client = _StubVkClient()
    notifier = _notifier(user=user, identity=None, client=client)

    with pytest.raises(UserNotReachable):
        await notifier.send_notification(_make_notification(user.id))
    assert client.calls == []


async def test_messages_not_allowed_is_unreachable() -> None:
    user = _make_user()
    # 901: the user never allowed the group to message them.
    client = _StubVkClient(VkApiError(code=901, message="not allowed"))
    notifier = _notifier(user=user, identity=_identity_for(user), client=client)

    with pytest.raises(UserNotReachable):
        await notifier.send_notification(_make_notification(user.id))


async def test_flood_control_asks_to_retry() -> None:
    user = _make_user()
    # 6: too many requests — a transient condition worth retrying.
    client = _StubVkClient(VkApiError(code=6, message="too many requests"))
    notifier = _notifier(user=user, identity=_identity_for(user), client=client)

    with pytest.raises(NotificationRetryAfter):
        await notifier.send_notification(_make_notification(user.id))


async def test_invalid_token_is_channel_unavailable() -> None:
    user = _make_user()
    # 5: authorization failed — a channel-wide misconfiguration. The consumer
    # drops the message rather than redelivering forever against a bad token.
    client = _StubVkClient(VkApiError(code=5, message="auth failed"))
    notifier = _notifier(user=user, identity=_identity_for(user), client=client)

    with pytest.raises(NotificationChannelUnavailable):
        await notifier.send_notification(_make_notification(user.id))


async def test_unknown_error_propagates() -> None:
    user = _make_user()
    client = _StubVkClient(VkApiError(code=100500, message="mystery"))
    notifier = _notifier(user=user, identity=_identity_for(user), client=client)

    with pytest.raises(VkApiError):
        await notifier.send_notification(_make_notification(user.id))
