from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.events.notifications import NotificationQueued
from fanfan.core.models.notification import NewNotification
from fanfan.core.vo.notification import NotificationType, generate_notification_id


class SendTestNotification:
    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        events_broker: EventBroker,
    ) -> None:
        self.current_user_provider = current_user_provider
        self.events_broker = events_broker

    async def __call__(self) -> None:
        current_user_id = await self.current_user_provider.require_user_id()

        # Tests all user notification channels with a single shared notification.
        await self.events_broker.publish(
            NotificationQueued(
                notification=NewNotification(
                    id=generate_notification_id(),
                    user_id=current_user_id,
                    title="Тестовое уведомление",
                    body=(
                        "Проверка каналов уведомлений.\n"
                        "Если канал подключён, вы должны получить это сообщение."
                    ),
                    # Test pushes only verify delivery; root is a safe landing.
                    path="/",
                    type=NotificationType.TEST,
                    mailing_id=None,
                )
            )
        )
