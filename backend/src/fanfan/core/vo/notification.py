from datetime import timedelta
from enum import StrEnum
from typing import NewType
from uuid import NAMESPACE_URL, UUID, uuid5, uuid7

from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.schedule_change import ScheduleChangeId
from fanfan.core.vo.user import UserId

NotificationId = NewType("NotificationId", UUID)

# How long a schedule notification stays worth delivering. Its text describes
# the programme as it was when it was built ("on stage now"), so past this age
# it is wrong rather than late: the fan-out drops a change this old, the
# channels drop a notification this old, and a push asks the push service to
# discard it by then.
SCHEDULE_NOTIFICATION_LIFETIME = timedelta(minutes=10)


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
    """Deterministic id for a change announcement notification.

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
    # Quest points awarded or taken back.
    QUEST = "quest"
    BROADCAST = "broadcast"
    # Self-test triggered from the profile page. The service worker always shows
    # the OS-level push for this type, even when the app is visible, so the user
    # can verify push delivery without backgrounding the app.
    TEST = "test"

    @property
    def is_time_sensitive(self) -> bool:
        """Whether the reader needs it now, not whenever the phone next syncs.

        The schedule moving, and organizers writing to people (everyone, or one
        person) while the festival runs. Quest points and tests can wait for a
        battery-saving phone to wake up.
        """
        return self in (
            NotificationType.SCHEDULE_CHANGE,
            NotificationType.SCHEDULE_SUBSCRIPTION,
            NotificationType.BROADCAST,
            NotificationType.MESSAGE,
        )

    @property
    def is_replaced_by_later(self) -> bool:
        """Whether a later notification of this type makes an earlier one moot.

        The stage announcement and the editors' notice describe the programme
        as a whole, so the latest one is all a reader needs. A subscription
        notice is about one act: a later one may be about another act and
        leaves the earlier one standing.
        """
        return self is NotificationType.SCHEDULE_CHANGE

    @property
    def is_schedule(self) -> bool:
        return self in (
            NotificationType.SCHEDULE_CHANGE,
            NotificationType.SCHEDULE_SUBSCRIPTION,
        )
