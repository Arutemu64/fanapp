from uuid import uuid7

import pytest

from fanfan.application.interactors.notifications.send_notification import (
    SendNotification,
    SendNotificationInput,
)
from fanfan.application.ports.notifier import TelegramTarget
from fanfan.core.exceptions.notifications import MailingAlreadyCancelled
from fanfan.core.models.notification import Notification
from fanfan.core.vo.mailing import MailingId, MailingStatus
from fanfan.core.vo.notification import NotificationType, generate_notification_id
from fanfan.core.vo.user import UserId

pytestmark = pytest.mark.unit

USER_ID = UserId(uuid7())


def _notification(*, mailing_id: MailingId | None = None) -> Notification:
    return Notification(
        id=generate_notification_id(),
        user_id=USER_ID,
        title="Внимание",
        body="Тело",
        type=NotificationType.DEFAULT,
        path="/schedule",
        mailing_id=mailing_id,
        seen_at=None,
    )


class _MailingDTO:
    """Minimal stand-in for MailingDTO — only ``status`` is read here."""

    def __init__(self, status: MailingStatus) -> None:
        self.status = status


class _StubNotificationGateway:
    def __init__(self, notification: Notification, log: list[str]) -> None:
        self._notification = notification
        self._log = log

    async def get(self, notification_id) -> Notification:  # noqa: ARG002
        self._log.append("read_notification")
        return self._notification


class _StubMailingGateway:
    def __init__(self, dto: _MailingDTO | None, log: list[str]) -> None:
        self._dto = dto
        self._log = log

    async def read_mailing(self, mailing_id) -> _MailingDTO | None:  # noqa: ARG002
        self._log.append("read_mailing")
        return self._dto


class _OrderRecordingNotifier:
    """Telegram-shaped notifier that records the order of its two phases."""

    def __init__(self, log: list[str]) -> None:
        self._log = log
        self.delivered: list[Notification] = []

    async def resolve(self, notification: Notification) -> TelegramTarget:  # noqa: ARG002
        self._log.append("resolve")
        return TelegramTarget(chat_id=1)

    async def deliver(
        self,
        notification: Notification,
        target: TelegramTarget,  # noqa: ARG002
    ) -> None:
        self._log.append("deliver")
        self.delivered.append(notification)


class _RecordingUow:
    def __init__(self, log: list[str]) -> None:
        self._log = log

    async def rollback(self) -> None:
        self._log.append("rollback")

    async def commit(self) -> None:
        self._log.append("commit")


def _interactor(
    *,
    notification: Notification,
    mailing: _MailingDTO | None,
    log: list[str],
) -> tuple[SendNotification, _OrderRecordingNotifier]:
    notifier = _OrderRecordingNotifier(log)
    interactor = SendNotification(
        mailing_gateway=_StubMailingGateway(mailing, log),  # type: ignore[arg-type]
        notification_gateway=_StubNotificationGateway(notification, log),  # type: ignore[arg-type]
        tg_notifier=notifier,  # type: ignore[arg-type]
        push_notifier=notifier,  # type: ignore[arg-type]
        vk_notifier=notifier,  # type: ignore[arg-type]
        uow=_RecordingUow(log),  # type: ignore[arg-type]
    )
    return interactor, notifier


async def test_read_transaction_is_closed_between_resolve_and_deliver() -> None:
    # The whole point of the two-phase port: every DB read (notification, then
    # the channel recipient) happens first, the transaction is rolled back to
    # release the connection, and only then does the network send run.
    log: list[str] = []
    notification = _notification()
    interactor, notifier = _interactor(notification=notification, mailing=None, log=log)

    await interactor.send_notification_to_telegram(
        SendNotificationInput(notification_id=notification.id)
    )

    assert log == ["read_notification", "resolve", "rollback", "deliver"]
    assert notifier.delivered == [notification]


async def test_active_mailing_is_read_before_the_send() -> None:
    log: list[str] = []
    mailing_id = MailingId(uuid7())
    notification = _notification(mailing_id=mailing_id)
    interactor, _ = _interactor(
        notification=notification,
        mailing=_MailingDTO(MailingStatus.SENDING),
        log=log,
    )

    await interactor.send_notification_to_telegram(
        SendNotificationInput(notification_id=notification.id)
    )

    assert log == [
        "read_notification",
        "read_mailing",
        "resolve",
        "rollback",
        "deliver",
    ]


async def test_cancelled_mailing_stops_before_resolving_or_delivering() -> None:
    log: list[str] = []
    mailing_id = MailingId(uuid7())
    notification = _notification(mailing_id=mailing_id)
    interactor, notifier = _interactor(
        notification=notification,
        mailing=_MailingDTO(MailingStatus.CANCELLED),
        log=log,
    )

    with pytest.raises(MailingAlreadyCancelled):
        await interactor.send_notification_to_telegram(
            SendNotificationInput(notification_id=notification.id)
        )

    # A cancelled mailing never reaches the network — nor even the recipient read.
    assert log == ["read_notification", "read_mailing"]
    assert notifier.delivered == []
