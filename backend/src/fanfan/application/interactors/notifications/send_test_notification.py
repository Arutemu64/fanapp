from fanfan.application.ports.cooldown import Cooldown
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.events.notifications import NotificationQueued
from fanfan.core.exceptions.notifications import TestNotificationTooFast
from fanfan.core.exceptions.rate_limit import CooldownActive
from fanfan.core.models.notification import NewNotification
from fanfan.core.vo.notification import NotificationType, generate_notification_id

# Each test fans out to every connected channel, VK included, so repeated taps
# would send a burst of identical messages through each one.
TEST_NOTIFICATION_COOLDOWN_SECONDS = 60


class SendTestNotification:
    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        events_broker: EventBroker,
        cooldown: Cooldown,
    ) -> None:
        self.current_user_provider = current_user_provider
        self.events_broker = events_broker
        self.cooldown = cooldown

    async def __call__(self) -> None:
        current_user_id = await self.current_user_provider.require_user_id()

        claim = self.cooldown.claim(
            f"test_notification:{current_user_id}", TEST_NOTIFICATION_COOLDOWN_SECONDS
        )
        try:
            async with claim:
                # Tests all user notification channels with a single shared
                # notification.
                await self.events_broker.publish(
                    NotificationQueued(
                        notification=NewNotification(
                            id=generate_notification_id(),
                            user_id=current_user_id,
                            title="Тестовое уведомление",
                            body=(
                                "Проверка каналов уведомлений.\n"
                                "Если канал подключён, ты получишь это сообщение."
                            ),
                            # Test pushes only verify delivery; root is a safe
                            # landing.
                            path="/",
                            type=NotificationType.TEST,
                            mailing_id=None,
                        )
                    )
                )
        except CooldownActive as e:
            raise TestNotificationTooFast(retry_after=e.details["retry_after"]) from e
