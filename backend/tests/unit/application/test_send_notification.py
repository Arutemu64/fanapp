from collections.abc import Awaitable, Callable
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
from fanfan.core.exceptions.notifications import UserNotReachable
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


def _make_notification() -> Notification:
    return Notification(
        id=NOTIFICATION_ID,
        user_id=USER_ID,
        title="Внимание",
        body="Тело",
        type=NotificationType.DEFAULT,
        path=None,
        mailing_id=None,
        seen_at=None,
    )


class _FakeNotificationGateway(NotificationGateway):
    def __init__(self, notification: Notification | None) -> None:
        self._notification = notification

    async def get(
        self,
        notification_id: object,  # noqa: ARG002  # part of the port contract
    ) -> Notification | None:
        return self._notification


class _FakeUserGateway(UserGateway):
    def __init__(self, user: User | None) -> None:
        self._user = user

    async def get_by_id(
        self,
        user_id: UserId,  # noqa: ARG002  # part of the port contract
    ) -> User | None:
        return self._user


class _StubMailingGateway(MailingGateway):
    async def get(
        self,
        mailing_id: MailingId,  # noqa: ARG002  # part of the port contract
    ) -> None:
        # Never called: these notifications carry no mailing_id.
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
        notification: Notification,  # noqa: ARG002  # part of the port contract
    ) -> None:
        self.commits_at_send = self._uow.commits


def _interactor(
    *,
    user: User | None,
    tg: FakeTelegramNotifier,
    push: FakePushNotifier,
    vk: FakeVkNotifier,
) -> SendNotification:
    return SendNotification(
        mailing_gateway=_StubMailingGateway(),
        notification_gateway=_FakeNotificationGateway(_make_notification()),
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
    # The loads take row locks; a send holding them would stall the mailing's
    # fan-out and every other channel of it for the length of the external call.
    uow = _FakeUow()
    notifier = _CommitCheckingNotifier(uow)
    interactor = SendNotification(
        mailing_gateway=_StubMailingGateway(),
        notification_gateway=_FakeNotificationGateway(_make_notification()),
        user_gateway=_FakeUserGateway(_make_user()),
        tg_notifier=notifier,
        push_notifier=notifier,
        vk_notifier=notifier,
        uow=uow,
    )

    await send(interactor, _INPUT)

    assert notifier.commits_at_send == 1


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
    # The opt-out is decided before the adapter is ever called.
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
    # Push has no per-channel setting — a live subscription is the opt-in — so it
    # delivers even when both messaging channels are switched off.
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
