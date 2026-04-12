from fanfan.application.dto.notification import NewNotificationDTO
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.id_provider import IdProvider
from fanfan.core.events.notifications import NewNotificationEvent
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.vo.notification import NotificationType


class SendTestNotification:
    def __init__(
        self,
        id_provider: IdProvider,
        events_broker: EventBroker,
    ) -> None:
        self.id_provider = id_provider
        self.events_broker = events_broker

    async def __call__(self) -> None:
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated

        # Проверяем все пользовательские каналы одним общим уведомлением.
        await self.events_broker.publish(
            NewNotificationEvent(
                notification=NewNotificationDTO(
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
