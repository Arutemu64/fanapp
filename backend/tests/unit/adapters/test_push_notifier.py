import json
from base64 import urlsafe_b64encode
from pathlib import Path
from uuid import uuid7

import httpx2
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from fanfan.adapters.push.client import MessageData, WebPushClient
from fanfan.adapters.push.config import PushConfig
from fanfan.adapters.push.push import PushNotifier
from fanfan.core.models.notification import Notification
from fanfan.core.models.push_subscription import PushSubscription
from fanfan.core.vo.notification import NotificationType, generate_notification_id
from fanfan.core.vo.push_subscription import generate_push_subscription_id
from fanfan.core.vo.user import UserId
from fanfan.main.generate_vapid import write_vapid_keys

pytestmark = pytest.mark.unit

USER_ID = UserId(uuid7())


def _b64url(raw: bytes) -> str:
    # Browsers send the keys base64url-encoded without padding.
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
        "tag": "42",
        "title": "Внимание",
        "body": "Тело уведомления",
        "url": "/schedule",
        "test": False,
    }


# --- WebPushClient.send: the flat domain model → nested library shape ----------


async def test_send_posts_encrypted_push_to_endpoint(tmp_path: Path) -> None:
    endpoint = "https://push.example/send/abc"
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(201)

    client = _client(tmp_path, httpx2.MockTransport(handler))

    status = await client.send(
        subscription=_browser_subscription(endpoint=endpoint),
        message_data=_message_data(),
    )

    # A malformed subscription (the flat dict the notifier used to pass) would
    # raise inside the library before any request went out; reaching the
    # endpoint at all is the regression guard.
    assert status == 201
    assert len(requests) == 1
    sent = requests[0]
    assert str(sent.url) == endpoint
    assert sent.headers["content-encoding"] == "aes128gcm"
    assert sent.headers["authorization"].startswith("vapid ")
    # The payload is encrypted, so it must not carry the plaintext body.
    assert b"\xd0\xa2" not in sent.content  # "Т" in UTF-8 — the title's first byte


async def test_send_returns_gone_status(tmp_path: Path) -> None:
    client = _client(tmp_path, httpx2.MockTransport(lambda _: httpx2.Response(410)))

    status = await client.send(
        subscription=_browser_subscription(endpoint="https://push.example/x"),
        message_data=_message_data(),
    )

    assert status == 410


# --- PushNotifier: message shaping and pruning of dead subscriptions -----------


class _RecordingClient:
    """Stands in for WebPushClient, recording each send and replaying a status."""

    def __init__(self, *, status: int = 201) -> None:
        self._status = status
        self.calls: list[dict] = []

    def ensure_available(self) -> None:
        pass

    async def send(
        self, *, subscription: PushSubscription, message_data: MessageData
    ) -> int:
        self.calls.append({"subscription": subscription, "message_data": message_data})
        return self._status


class _StubGateway:
    def __init__(self, subs: list[PushSubscription]) -> None:
        self._subs = subs
        self.deleted: list[PushSubscription] = []

    async def list_by_user(
        self,
        user_id: UserId,  # noqa: ARG002  # part of the port contract
    ) -> list[PushSubscription]:
        return self._subs

    async def delete(self, model: PushSubscription) -> None:
        self.deleted.append(model)


class _StubUow:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def _notification(
    notification_type: NotificationType = NotificationType.DEFAULT,
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
    )


async def test_notifier_passes_domain_subscription_and_flattens_html() -> None:
    sub = _browser_subscription(endpoint="https://push.example/one")
    gateway = _StubGateway([sub])
    client = _RecordingClient()
    uow = _StubUow()
    notifier = PushNotifier(
        push_sub_gateway=gateway,  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
        client=client,  # type: ignore[arg-type]
    )

    await notifier.send_notification(_notification())

    # The read transaction is released before the network send, and nothing is
    # pruned here so no write is committed.
    assert uow.rollbacks == 1
    assert uow.commits == 0
    assert len(client.calls) == 1
    call = client.calls[0]
    # The unmapped domain aggregate is handed straight to the client.
    assert call["subscription"] is sub
    data = call["message_data"]
    # HTML is flattened to plain text; <br> becomes a newline.
    assert "<b>" not in data["body"]
    assert data["body"] == "Тело уведомления\nвторая строка"
    assert data["url"] == "/schedule"
    assert data["test"] is False


async def test_notifier_prunes_gone_subscription() -> None:
    live = _browser_subscription(endpoint="https://push.example/live")
    dead = _browser_subscription(endpoint="https://push.example/dead")
    gateway = _StubGateway([live, dead])
    uow = _StubUow()

    # 410 Gone for every send: both endpoints report themselves retired.
    notifier = PushNotifier(
        push_sub_gateway=gateway,  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
        client=_RecordingClient(status=410),  # type: ignore[arg-type]
    )

    await notifier.send_notification(_notification())

    assert gateway.deleted == [live, dead]
    assert uow.commits == 2


async def test_notifier_test_type_sets_foreground_flag() -> None:
    sub = _browser_subscription(endpoint="https://push.example/one")
    client = _RecordingClient()
    notifier = PushNotifier(
        push_sub_gateway=_StubGateway([sub]),  # type: ignore[arg-type]
        uow=_StubUow(),  # type: ignore[arg-type]
        client=client,  # type: ignore[arg-type]
    )

    await notifier.send_notification(_notification(NotificationType.TEST))

    assert client.calls[0]["message_data"]["test"] is True


def test_message_data_round_trips_as_json() -> None:
    # The library serializes the payload with json.dumps; every value must be
    # JSON-native, which is the contract the TypedDict encodes.
    assert json.loads(json.dumps(_message_data())) == _message_data()
