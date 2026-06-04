from fanfan.application.dto.notification import NewNotificationDTO
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.events.notifications import NotificationQueued
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

        # Проверяем все пользовательские каналы одним общим уведомлением.
        await self.events_broker.publish(
            NotificationQueued(
                notification=NewNotificationDTO(
                    id=generate_notification_id(),
                    user_id=current_user_id,
                    title="Тестовое уведомление",
                    body=(
                        "Проверка каналов уведомлений.\n"
                        "Если канал подключён, вы должны получить это сообщение."
                    ),
                    type=NotificationType.DEFAULT,
                    mailing_id=None,
                )
            )
        )
