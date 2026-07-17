import logging
from dataclasses import dataclass

from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.events.notifications import NotificationQueued
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.models.notification import NewNotification
from fanfan.core.vo.notification import NotificationType, generate_notification_id
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.user import UserId

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class SendPersonalNotificationInput:
    user_id: UserId
    message_text: str


class SendPersonalNotification:
    def __init__(
        self,
        user_gateway: UserGateway,
        mailing_gateway: MailingGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        events_broker: EventBroker,
    ):
        self.user_gateway = user_gateway
        self.mailing_gateway = mailing_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.events_broker = events_broker

    async def __call__(self, data: SendPersonalNotificationInput):
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, perm_name=Permission.NOTIFICATIONS_SEND
        )

        user = await self.user_gateway.get_by_id(data.user_id)
        if user is None:
            raise UserNotFound

        await self.events_broker.publish(
            NotificationQueued(
                notification=NewNotification(
                    id=generate_notification_id(),
                    user_id=user.id,
                    title="Личное сообщение",
                    body=data.message_text,
                    type=NotificationType.MESSAGE,
                    path="/notifications",
                    mailing_id=None,
                ),
            )
        )

        logger.info(
            "Personal notification sent",
            extra={
                "actor_id": str(current_user.id),
                "target_user_id": str(user.id),
            },
        )
