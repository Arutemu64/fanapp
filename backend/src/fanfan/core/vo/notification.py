from enum import StrEnum
from typing import NewType
from uuid import NAMESPACE_URL, UUID, uuid5, uuid7

from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.schedule_change import ScheduleChangeId
from fanfan.core.vo.user import UserId

NotificationId = NewType("NotificationId", UUID)


def generate_notification_id() -> NotificationId:
    return NotificationId(uuid7())


def notification_id_for(mailing_id: MailingId, user_id: UserId) -> NotificationId:
    """Deterministic id for a mailing's per-user notification.

    A redelivered fan-out must produce the same ids so the insert can be an
    idempotent no-op instead of a duplicate.
    """
    return NotificationId(uuid5(NAMESPACE_URL, f"notification:{mailing_id}:{user_id}"))


def schedule_notification_id_for(
    schedule_change_id: ScheduleChangeId,
    user_id: UserId,
    discriminator: str,
) -> NotificationId:
    """Deterministic id for a schedule-change fan-out notification.

    The schedule-change trigger is redelivered at-least-once; a rerun that
    minted fresh random ids would slip past the notifications insert's
    on-conflict-do-nothing dedup and duplicate every recipient's notification
    (and drift the mailing's sent_count past total_count). The schedule change
    id is the stable anchor across redeliveries; the discriminator separates the
    distinct notifications one user can receive from a single change — an editor
    notice, a global announcement, a per-subscription notice — so they keep
    distinct ids instead of collapsing into one.
    """
    return NotificationId(
        uuid5(
            NAMESPACE_URL,
            f"schedule_notification:{schedule_change_id}:{user_id}:{discriminator}",
        )
    )


class NotificationType(StrEnum):
    DEFAULT = "default"
    SCHEDULE_CHANGE = "schedule_change"
    SCHEDULE_SUBSCRIPTION = "schedule_subscription"
    MESSAGE = "message"
    POINTS_RECEIVED = "points_received"
    BROADCAST = "broadcast"
    # Self-test triggered from the profile page. The service worker always shows
    # the OS-level push for this type, even when the app is visible, so the user
    # can verify push delivery without backgrounding the app.
    TEST = "test"
