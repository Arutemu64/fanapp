from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid7

import pytest

from fanfan.application.interactors.notifications.send_notification import (
    SendNotification,
    SendNotificationInput,
)
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.notifier import (
    PushNotifierPort,
    TelegramNotifierPort,
    VkNotifierPort,
)
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.notifications import (
    NotificationExpired,
    NotificationSuperseded,
    UserNotReachable,
)
from fanfan.core.models.notification import Notification
from fanfan.core.models.user import User, UserSettings
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationType, generate_notification_id
from fanfan.core.vo.user import UserId, Username, UserRole
from tests.fakes.notifier import (
    FakePushNotifier,
    FakeTelegramNotifier,
    FakeVkNotifier,
)

pytestmark = pytest.mark.unit

USER_ID = UserId(uuid7())
NOTIFICATION_ID = generate_notification_id()


def _make_user(*, telegram: bool = True, vk: bool = True) -> User:
    return User(
        id=USER_ID,
        username=Username("tester"),
        hashed_password=None,
        role=UserRole.VISITOR,
        settings=UserSettings(
            receive_telegram_notifications=telegram,
            receive_vk_notifications=vk,
        ),
    )


def _make_notification(
    *,
    notification_type: NotificationType = NotificationType.DEFAULT,
    age: timedelta = timedelta(0),
) -> Notification:
    return Notification(
        id=NOTIFICATION_ID,
        user_id=USER_ID,
        title="Внимание",
        body="Тело",
        type=notification_type,
        path=None,
        mailing_id=None,
        seen_at=None,
        created_at=datetime.now(UTC) - age,
    )


class _FakeNotificationGateway(NotificationGateway):
    def __init__(
        self, notification: Notification | None, *, superseded: bool = False
    ) -> None:
        self._notification = notification
        self._superseded = superseded
        self.locked_reads = 0

    async def is_superseded(
        self,
        notification: Notification,  # noqa: ARG002
    ) -> bool:
        return self._superseded

    async def get(
        self,
        notification_id: object,  # noqa: ARG002
        *,
        lock: bool = True,
    ) -> Notification | None:
        if lock:
            self.locked_reads += 1
        return self._notification


class _FakeUserGateway(UserGateway):
    def __init__(self, user: User | None) -> None:
        self._user = user

    async def get_by_id(
        self,
        user_id: UserId,  # noqa: ARG002
    ) -> User | None:
        return self._user


class _StubMailingGateway(MailingGateway):
    async def get(
        self,
        mailing_id: MailingId,  # noqa: ARG002
        *,
        lock: bool = True,  # noqa: ARG002
    ) -> None:
        msg = "mailing gateway should not be queried"
        raise AssertionError(msg)


class _FakeUow(UnitOfWork):
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class _CommitCheckingNotifier(TelegramNotifierPort, PushNotifierPort, VkNotifierPort):
    """Records how many commits had run when the external send started."""

    def __init__(self, uow: _FakeUow) -> None:
        self._uow = uow
        self.commits_at_send: int | None = None

    async def send_notification(
        self,
        notification: Notification,  # noqa: ARG002
    ) -> None:
        self.commits_at_send = self._uow.commits


def _interactor(
    *,
    user: User | None,
    tg: FakeTelegramNotifier,
    push: FakePushNotifier,
    vk: FakeVkNotifier,
    notification: Notification | None = None,
    superseded: bool = False,
) -> SendNotification:
    return SendNotification(
        mailing_gateway=_StubMailingGateway(),
        notification_gateway=_FakeNotificationGateway(
            notification or _make_notification(), superseded=superseded
        ),
        user_gateway=_FakeUserGateway(user),
        tg_notifier=tg,
        push_notifier=push,
        vk_notifier=vk,
        uow=_FakeUow(),
    )


_INPUT = SendNotificationInput(notification_id=NOTIFICATION_ID)


async def test_telegram_delivered_when_enabled() -> None:
    tg = FakeTelegramNotifier()
    interactor = _interactor(
        user=_make_user(telegram=True),
        tg=tg,
        push=FakePushNotifier(),
        vk=FakeVkNotifier(),
    )

    await interactor.send_notification_to_telegram(_INPUT)

    assert [n.id for n in tg.sent_notifications] == [NOTIFICATION_ID]


@pytest.mark.parametrize(
    "send",
    [
        SendNotification.send_notification_to_telegram,
        SendNotification.send_notification_to_push,
        SendNotification.send_notification_to_vk,
    ],
)
async def test_read_transaction_ends_before_the_external_send(
    send: Callable[[SendNotification, SendNotificationInput], Awaitable[None]],
) -> None:
    uow = _FakeUow()
    notifier = _CommitCheckingNotifier(uow)
    notification_gateway = _FakeNotificationGateway(_make_notification())
    interactor = SendNotification(
        mailing_gateway=_StubMailingGateway(),
        notification_gateway=notification_gateway,
        user_gateway=_FakeUserGateway(_make_user()),
        tg_notifier=notifier,
        push_notifier=notifier,
        vk_notifier=notifier,
        uow=uow,
    )

    await send(interactor, _INPUT)

    assert notifier.commits_at_send == 1
    assert notification_gateway.locked_reads == 0


@pytest.mark.parametrize(
    "notification_type",
    [NotificationType.SCHEDULE_CHANGE, NotificationType.SCHEDULE_SUBSCRIPTION],
)
async def test_stale_schedule_notification_is_expired_not_sent(
    notification_type: NotificationType,
) -> None:
    push = FakePushNotifier()
    interactor = _interactor(
        user=_make_user(),
        tg=FakeTelegramNotifier(),
        push=push,
        vk=FakeVkNotifier(),
        notification=_make_notification(
            notification_type=notification_type, age=timedelta(minutes=11)
        ),
    )

    with pytest.raises(NotificationExpired):
        await interactor.send_notification_to_push(_INPUT)
    assert push.sent_notifications == []


async def test_fresh_schedule_notification_is_sent() -> None:
    push = FakePushNotifier()
    interactor = _interactor(
        user=_make_user(),
        tg=FakeTelegramNotifier(),
        push=push,
        vk=FakeVkNotifier(),
        notification=_make_notification(
            notification_type=NotificationType.SCHEDULE_CHANGE,
            age=timedelta(minutes=9),
        ),
    )

    await interactor.send_notification_to_push(_INPUT)

    assert [n.id for n in push.sent_notifications] == [NOTIFICATION_ID]


@pytest.mark.parametrize(
    "send",
    [
        SendNotification.send_notification_to_telegram,
        SendNotification.send_notification_to_push,
        SendNotification.send_notification_to_vk,
    ],
)
async def test_superseded_schedule_notification_is_not_sent(
    send: Callable[[SendNotification, SendNotificationInput], Awaitable[None]],
) -> None:
    tg, push, vk = FakeTelegramNotifier(), FakePushNotifier(), FakeVkNotifier()
    interactor = _interactor(
        user=_make_user(),
        tg=tg,
        push=push,
        vk=vk,
        notification=_make_notification(
            notification_type=NotificationType.SCHEDULE_CHANGE
        ),
        superseded=True,
    )

    with pytest.raises(NotificationSuperseded):
        await send(interactor, _INPUT)
    assert tg.sent_notifications == push.sent_notifications == []
    assert vk.sent_notifications == []


@pytest.mark.parametrize(
    "notification_type",
    [NotificationType.SCHEDULE_SUBSCRIPTION, NotificationType.BROADCAST],
)
async def test_only_stage_notices_can_be_superseded(
    notification_type: NotificationType,
) -> None:
    push = FakePushNotifier()
    interactor = _interactor(
        user=_make_user(),
        tg=FakeTelegramNotifier(),
        push=push,
        vk=FakeVkNotifier(),
        notification=_make_notification(notification_type=notification_type),
        superseded=True,
    )

    await interactor.send_notification_to_push(_INPUT)

    assert [n.id for n in push.sent_notifications] == [NOTIFICATION_ID]


async def test_late_broadcast_is_still_sent() -> None:
    push = FakePushNotifier()
    interactor = _interactor(
        user=_make_user(),
        tg=FakeTelegramNotifier(),
        push=push,
        vk=FakeVkNotifier(),
        notification=_make_notification(
            notification_type=NotificationType.BROADCAST, age=timedelta(hours=1)
        ),
    )

    await interactor.send_notification_to_push(_INPUT)

    assert [n.id for n in push.sent_notifications] == [NOTIFICATION_ID]


async def test_telegram_opt_out_is_unreachable() -> None:
    tg = FakeTelegramNotifier()
    interactor = _interactor(
        user=_make_user(telegram=False),
        tg=tg,
        push=FakePushNotifier(),
        vk=FakeVkNotifier(),
    )

    with pytest.raises(UserNotReachable):
        await interactor.send_notification_to_telegram(_INPUT)
    assert tg.sent_notifications == []


async def test_vk_delivered_when_enabled() -> None:
    vk = FakeVkNotifier()
    interactor = _interactor(
        user=_make_user(vk=True),
        tg=FakeTelegramNotifier(),
        push=FakePushNotifier(),
        vk=vk,
    )

    await interactor.send_notification_to_vk(_INPUT)

    assert [n.id for n in vk.sent_notifications] == [NOTIFICATION_ID]


async def test_vk_opt_out_is_unreachable() -> None:
    vk = FakeVkNotifier()
    interactor = _interactor(
        user=_make_user(vk=False),
        tg=FakeTelegramNotifier(),
        push=FakePushNotifier(),
        vk=vk,
    )

    with pytest.raises(UserNotReachable):
        await interactor.send_notification_to_vk(_INPUT)
    assert vk.sent_notifications == []


async def test_push_ignores_channel_opt_outs() -> None:
    push = FakePushNotifier()
    interactor = _interactor(
        user=_make_user(telegram=False, vk=False),
        tg=FakeTelegramNotifier(),
        push=push,
        vk=FakeVkNotifier(),
    )

    await interactor.send_notification_to_push(_INPUT)

    assert [n.id for n in push.sent_notifications] == [NOTIFICATION_ID]


async def test_missing_user_is_unreachable() -> None:
    tg = FakeTelegramNotifier()
    interactor = _interactor(
        user=None, tg=tg, push=FakePushNotifier(), vk=FakeVkNotifier()
    )

    with pytest.raises(UserNotReachable):
        await interactor.send_notification_to_telegram(_INPUT)
    assert tg.sent_notifications == []
