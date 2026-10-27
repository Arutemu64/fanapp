import json
import re
from base64 import urlsafe_b64encode
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, override
from uuid import uuid7

import httpx2
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import HttpUrl, SecretStr

from fanfan.adapters.push.client import MessageData, PushUrgency, WebPushClient
from fanfan.adapters.push.config import PushConfig
from fanfan.adapters.push.push import PushNotifier
from fanfan.application.ports.gateways.push_subscriptions import (
    PushSubscriptionGateway,
)
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.notifications import (
    NotificationChannelUnavailable,
    NotificationRetryAfter,
)
from fanfan.core.models.notification import Notification
from fanfan.core.models.push_subscription import PushSubscription
from fanfan.core.vo.notification import NotificationType, generate_notification_id
from fanfan.core.vo.push_subscription import generate_push_subscription_id
from fanfan.core.vo.schedule_entry import generate_schedule_entry_id
from fanfan.core.vo.user import UserId
from fanfan.main.generate_vapid import write_vapid_keys
from fanfan.presentation.web.config import WebConfig

pytestmark = pytest.mark.unit

USER_ID = UserId(uuid7())
WEB_CONFIG = WebConfig(
    host="127.0.0.1",
    port=8000,
    public_url=HttpUrl("https://fanfan.example/"),
    secret_key=SecretStr("test-secret"),
)


def _b64url(raw: bytes) -> str:
    return urlsafe_b64encode(raw).rstrip(b"=").decode()


def _browser_subscription(*, endpoint: str) -> PushSubscription:
    """A subscription with a real P-256 public key, as a browser would send.

    The p256dh must be a valid curve point or the library's ECDH encryption
    raises, so mint a throwaway keypair rather than using a random string.
    """
    private_key = ec.generate_private_key(ec.SECP256R1())
    p256dh = private_key.public_key().public_bytes(
        Encoding.X962, PublicFormat.UncompressedPoint
    )
    return PushSubscription(
        id=generate_push_subscription_id(),
        user_id=USER_ID,
        endpoint=endpoint,
        p256dh=_b64url(p256dh),
        auth=_b64url(b"0123456789abcdef"),
    )


def _client(tmp_path: Path, transport: httpx2.MockTransport) -> WebPushClient:
    write_vapid_keys(tmp_path)
    config = PushConfig(
        private_key_path=tmp_path / "private_key.pem",
        public_key_path=tmp_path / "public_key.pem",
        subscriber="mailto:push@example.com",
    )
    http = httpx2.AsyncClient(transport=transport)
    return WebPushClient(client=http, config=config)


def _message_data() -> MessageData:
    return {
        "web_push": 8030,
        "mutable": True,
        "notification": {
            "title": "Внимание",
            "body": "Тело уведомления",
            "navigate": "https://fanfan.example/schedule",
            "tag": "42",
            "renotify": False,
            "data": {"test": False},
        },
    }


async def test_send_posts_encrypted_push_to_endpoint(tmp_path: Path) -> None:
    endpoint = "https://push.example/send/abc"
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(201)

    client = _client(tmp_path, httpx2.MockTransport(handler))

    response = await client.send(
        subscription=_browser_subscription(endpoint=endpoint),
        message_data=_message_data(),
        ttl_seconds=600,
        urgency="high",
        topic="schedule",
    )

    assert response.status_code == 201
    assert len(requests) == 1
    sent = requests[0]
    assert str(sent.url) == endpoint
    assert sent.headers["content-encoding"] == "aes128gcm"
    assert sent.headers["authorization"].startswith("vapid ")
    assert sent.headers["ttl"] == "600"
    assert sent.headers["urgency"] == "high"
    assert sent.headers["topic"] == "schedule"
    assert _message_data()["notification"]["body"].encode() not in sent.content


async def test_send_returns_response_with_status(tmp_path: Path) -> None:
    client = _client(tmp_path, httpx2.MockTransport(lambda _: httpx2.Response(410)))

    response = await client.send(
        subscription=_browser_subscription(endpoint="https://push.example/x"),
        message_data=_message_data(),
        ttl_seconds=3600,
        urgency="normal",
        topic=None,
    )

    assert response.status_code == 410
    assert "topic" not in response.request.headers


class _RecordingClient(WebPushClient):
    """Stands in for WebPushClient, recording each send and replaying a response.

    Subclasses the real client (rather than duck-typing it) so `ty` verifies the
    overrides against the signatures the notifier actually calls. `__init__` does
    not call super(): there is no VAPID keypair or httpx pool here, and both
    overridden methods replace every use of them.
    """

    def __init__(
        self,
        *,
        status: int = 201,
        headers: dict[str, str] | None = None,
        fail_endpoints: frozenset[str] = frozenset(),
    ) -> None:
        self._status = status
        self._headers = headers or {}
        self._fail_endpoints = fail_endpoints
        self.calls: list[dict[str, Any]] = []

    @override
    def ensure_available(self) -> None:
        pass

    @override
    async def send(
        self,
        *,
        subscription: PushSubscription,
        message_data: MessageData,
        ttl_seconds: int,
        urgency: PushUrgency,
        topic: str | None,
    ) -> httpx2.Response:
        self.calls.append(
            {
                "subscription": subscription,
                "message_data": message_data,
                "ttl_seconds": ttl_seconds,
                "urgency": urgency,
                "topic": topic,
            }
        )
        if subscription.endpoint in self._fail_endpoints:
            msg = "push service unreachable"
            raise httpx2.ConnectError(msg)
        return httpx2.Response(self._status, headers=self._headers)


class _StubGateway(PushSubscriptionGateway):
    def __init__(self, subs: list[PushSubscription]) -> None:
        self._subs = subs
        self.deleted: list[PushSubscription] = []

    @override
    async def list_by_user(
        self,
        user_id: UserId,
    ) -> list[PushSubscription]:
        return self._subs

    @override
    async def delete(self, model: PushSubscription) -> None:
        self.deleted.append(model)


class _StubUow(UnitOfWork):
    def __init__(self) -> None:
        self.commits = 0

    @override
    async def commit(self) -> None:
        self.commits += 1


def _notification(
    notification_type: NotificationType = NotificationType.DEFAULT,
    *,
    created_at: datetime | None = None,
) -> Notification:
    return Notification(
        id=generate_notification_id(),
        user_id=USER_ID,
        title="Внимание",
        body="Тело <b>уведомления</b><br>вторая строка",
        type=notification_type,
        path="/schedule",
        mailing_id=None,
        seen_at=None,
        created_at=created_at,
    )


async def test_notifier_passes_domain_subscription_and_flattens_html() -> None:
    sub = _browser_subscription(endpoint="https://push.example/one")
    gateway = _StubGateway([sub])
    client = _RecordingClient()
    notifier = PushNotifier(
        push_sub_gateway=gateway,
        uow=_StubUow(),
        client=client,
        web_config=WEB_CONFIG,
    )

    await notifier.send_notification(_notification())

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["subscription"] is sub
    data = call["message_data"]["notification"]
    assert "<b>" not in data["body"]
    assert data["body"] == "Тело уведомления\nвторая строка"
    assert data["navigate"] == "https://fanfan.example/schedule"
    assert data["data"] == {"test": False}
    assert data["tag"] not in {"schedule", "subscription", "broadcast"}
    assert data["renotify"] is False


@pytest.mark.parametrize(
    ("notification_type", "expected_tag"),
    [
        (NotificationType.SCHEDULE_CHANGE, "schedule"),
        (NotificationType.SCHEDULE_SUBSCRIPTION, "subscription"),
        (NotificationType.BROADCAST, "broadcast"),
    ],
)
async def test_notifier_groups_topic_notifications_by_tag(
    notification_type: NotificationType, expected_tag: str
) -> None:
    """Schedule and broadcast pushes share a topic tag (and re-alert on replace),
    so a burst collapses to the latest instead of stacking on the OS shade."""
    sub = _browser_subscription(endpoint="https://push.example/one")
    notifier = PushNotifier(
        push_sub_gateway=_StubGateway([sub]),
        uow=_StubUow(),
        client=(client := _RecordingClient()),
        web_config=WEB_CONFIG,
    )

    await notifier.send_notification(_notification(notification_type))

    data = client.calls[0]["message_data"]["notification"]
    assert data["tag"] == expected_tag
    assert data["renotify"] is True


async def test_notifier_gives_each_subscribed_act_its_own_lane() -> None:
    """Notices about two acts close in the running order both stay on the
    shade; a later notice about the same act replaces the earlier one."""
    sub = _browser_subscription(endpoint="https://push.example/one")
    notifier = PushNotifier(
        push_sub_gateway=_StubGateway([sub]),
        uow=_StubUow(),
        client=(client := _RecordingClient()),
        web_config=WEB_CONFIG,
    )
    first_act = generate_schedule_entry_id()
    second_act = generate_schedule_entry_id()

    for event_id in (first_act, second_act, first_act):
        notification = _notification(NotificationType.SCHEDULE_SUBSCRIPTION)
        notification.event_id = event_id
        await notifier.send_notification(notification)

    topics = [call["topic"] for call in client.calls]
    tags = [call["message_data"]["notification"]["tag"] for call in client.calls]
    assert topics == tags
    assert topics[0] == topics[2] != topics[1]
    assert all(len(topic) <= 32 for topic in topics)
    assert all(re.fullmatch(r"[A-Za-z0-9_-]+", topic) for topic in topics)


async def test_notifier_prunes_gone_subscription() -> None:
    live = _browser_subscription(endpoint="https://push.example/live")
    dead = _browser_subscription(endpoint="https://push.example/dead")
    gateway = _StubGateway([live, dead])
    uow = _StubUow()

    notifier = PushNotifier(
        push_sub_gateway=gateway,
        uow=uow,
        client=_RecordingClient(status=410),
        web_config=WEB_CONFIG,
    )

    await notifier.send_notification(_notification())

    assert gateway.deleted == [live, dead]
    assert uow.commits == 3


async def test_notifier_ends_read_transaction_before_sending() -> None:
    uow = _StubUow()
    notifier = PushNotifier(
        push_sub_gateway=_StubGateway(
            [_browser_subscription(endpoint="https://push.example/one")]
        ),
        uow=uow,
        client=_RecordingClient(),
        web_config=WEB_CONFIG,
    )

    await notifier.send_notification(_notification())

    assert uow.commits == 1


@pytest.mark.parametrize(
    ("notification_type", "expected_topic"),
    [
        (NotificationType.SCHEDULE_CHANGE, "schedule"),
        (NotificationType.SCHEDULE_SUBSCRIPTION, "subscription"),
    ],
)
async def test_notifier_sends_schedule_pushes_urgent_and_short_lived(
    notification_type: NotificationType, expected_topic: str
) -> None:
    """A schedule push is a time-sensitive alert (RFC 8030 §5.3 "high"), lives
    only as long as its text is true, and replaces a still-queued one."""
    client = _RecordingClient()
    notifier = PushNotifier(
        push_sub_gateway=_StubGateway(
            [_browser_subscription(endpoint="https://push.example/one")]
        ),
        uow=_StubUow(),
        client=client,
        web_config=WEB_CONFIG,
    )

    await notifier.send_notification(_notification(notification_type))

    call = client.calls[0]
    assert call["urgency"] == "high"
    assert call["ttl_seconds"] == 600
    assert call["topic"] == expected_topic


async def test_notifier_gives_a_late_schedule_push_only_its_remaining_lifetime() -> (
    None
):
    """A push held by the push service must not outlive its text: four minutes
    into a ten-minute lifetime leaves six."""
    client = _RecordingClient()
    notifier = PushNotifier(
        push_sub_gateway=_StubGateway(
            [_browser_subscription(endpoint="https://push.example/one")]
        ),
        uow=_StubUow(),
        client=client,
        web_config=WEB_CONFIG,
    )
    created_at = datetime.now(UTC) - timedelta(minutes=4)

    await notifier.send_notification(
        _notification(NotificationType.SCHEDULE_CHANGE, created_at=created_at)
    )

    assert 355 <= client.calls[0]["ttl_seconds"] <= 360


@pytest.mark.parametrize(
    "notification_type", [NotificationType.BROADCAST, NotificationType.MESSAGE]
)
async def test_notifier_sends_organizer_messages_urgent_but_long_lived(
    notification_type: NotificationType,
) -> None:
    """An organizer writing to people mid-festival is time-sensitive, but its
    text stays true, so it keeps the default lifetime."""
    client = _RecordingClient()
    notifier = PushNotifier(
        push_sub_gateway=_StubGateway(
            [_browser_subscription(endpoint="https://push.example/one")]
        ),
        uow=_StubUow(),
        client=client,
        web_config=WEB_CONFIG,
    )

    await notifier.send_notification(_notification(notification_type))

    call = client.calls[0]
    assert call["urgency"] == "high"
    assert call["ttl_seconds"] == 3600


async def test_notifier_sends_other_pushes_at_normal_urgency_without_topic() -> None:
    client = _RecordingClient()
    notifier = PushNotifier(
        push_sub_gateway=_StubGateway(
            [_browser_subscription(endpoint="https://push.example/one")]
        ),
        uow=_StubUow(),
        client=client,
        web_config=WEB_CONFIG,
    )

    await notifier.send_notification(_notification())

    call = client.calls[0]
    assert call["urgency"] == "normal"
    assert call["ttl_seconds"] == 3600
    assert call["topic"] is None


async def test_notifier_sends_to_every_device_before_raising_a_send_error() -> None:
    broken = _browser_subscription(endpoint="https://push.example/broken")
    dead = _browser_subscription(endpoint="https://push.example/dead")
    gateway = _StubGateway([broken, dead])
    client = _RecordingClient(status=410, fail_endpoints=frozenset({broken.endpoint}))
    notifier = PushNotifier(
        push_sub_gateway=gateway,
        uow=_StubUow(),
        client=client,
        web_config=WEB_CONFIG,
    )

    with pytest.raises(httpx2.ConnectError):
        await notifier.send_notification(_notification())
    assert len(client.calls) == 2
    assert gateway.deleted == [dead]


async def test_notifier_decodes_html_entities_to_plain_text() -> None:
    sub = _browser_subscription(endpoint="https://push.example/one")
    client = _RecordingClient()
    notifier = PushNotifier(
        push_sub_gateway=_StubGateway([sub]),
        uow=_StubUow(),
        client=client,
        web_config=WEB_CONFIG,
    )
    notification = Notification(
        id=generate_notification_id(),
        user_id=USER_ID,
        title="Кафе «U & I»",
        body="Скидка 5 &lt; 10 &amp; выше",
        type=NotificationType.DEFAULT,
        path=None,
        mailing_id=None,
        seen_at=None,
    )

    await notifier.send_notification(notification)

    data = client.calls[0]["message_data"]["notification"]
    assert data["body"] == "Скидка 5 < 10 & выше"
    assert data["title"] == "Кафе «U & I»"
    assert data["navigate"] == "https://fanfan.example/"


async def test_notifier_raises_channel_unavailable_on_auth_failure() -> None:
    sub = _browser_subscription(endpoint="https://push.example/one")
    gateway = _StubGateway([sub])
    notifier = PushNotifier(
        push_sub_gateway=gateway,
        uow=_StubUow(),
        client=_RecordingClient(status=401),
        web_config=WEB_CONFIG,
    )

    with pytest.raises(NotificationChannelUnavailable):
        await notifier.send_notification(_notification())
    assert gateway.deleted == []


async def test_notifier_retries_on_throttle_with_default_backoff() -> None:
    notifier = PushNotifier(
        push_sub_gateway=_StubGateway(
            [_browser_subscription(endpoint="https://push.example/one")]
        ),
        uow=_StubUow(),
        client=_RecordingClient(status=429),
        web_config=WEB_CONFIG,
    )

    with pytest.raises(NotificationRetryAfter) as exc:
        await notifier.send_notification(_notification())
    assert exc.value.retry_after == 5


async def test_notifier_honors_retry_after_header() -> None:
    notifier = PushNotifier(
        push_sub_gateway=_StubGateway(
            [_browser_subscription(endpoint="https://push.example/one")]
        ),
        uow=_StubUow(),
        client=_RecordingClient(status=429, headers={"Retry-After": "30"}),
        web_config=WEB_CONFIG,
    )

    with pytest.raises(NotificationRetryAfter) as exc:
        await notifier.send_notification(_notification())
    assert exc.value.retry_after == 30


async def test_notifier_retries_on_server_error() -> None:
    notifier = PushNotifier(
        push_sub_gateway=_StubGateway(
            [_browser_subscription(endpoint="https://push.example/one")]
        ),
        uow=_StubUow(),
        client=_RecordingClient(status=503),
        web_config=WEB_CONFIG,
    )

    with pytest.raises(NotificationRetryAfter):
        await notifier.send_notification(_notification())


async def test_notifier_test_type_sets_foreground_flag() -> None:
    sub = _browser_subscription(endpoint="https://push.example/one")
    client = _RecordingClient()
    notifier = PushNotifier(
        push_sub_gateway=_StubGateway([sub]),
        uow=_StubUow(),
        client=client,
        web_config=WEB_CONFIG,
    )

    await notifier.send_notification(_notification(NotificationType.TEST))

    assert client.calls[0]["message_data"]["notification"]["data"]["test"] is True


async def test_notifier_sends_declarative_web_push_message() -> None:
    """Safari parses the message itself only when it opts in with `web_push: 8030`;
    `mutable` keeps the service worker's `push` handler running there."""
    client = _RecordingClient()
    notifier = PushNotifier(
        push_sub_gateway=_StubGateway(
            [_browser_subscription(endpoint="https://push.example/one")]
        ),
        uow=_StubUow(),
        client=client,
        web_config=WEB_CONFIG,
    )

    await notifier.send_notification(_notification())

    message = client.calls[0]["message_data"]
    assert message["web_push"] == 8030
    assert message["mutable"] is True
    assert message["notification"]["title"] == "Внимание"


def test_message_data_round_trips_as_json() -> None:
    assert json.loads(json.dumps(_message_data())) == _message_data()
