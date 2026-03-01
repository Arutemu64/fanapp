import logging
from dataclasses import dataclass

from fanfan.adapters.db.gateways.mailings import MailingGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.nats.events_broker import EventBroker
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.dto.notification import NewNotificationDTO
from fanfan.core.events.notifications import NewNotificationEvent
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.vo.notification import NotificationType
from fanfan.core.vo.user import UserId, UserRole

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class SendMessageCommand:
    user_id: UserId
    message_text: str


class SendMessage:
    def __init__(
        self,
        user_gateway: UserGateway,
        mailing_gateway: MailingGateway,
        id_provider: IdProvider,
        events_broker: EventBroker,
    ):
        self.user_gateway = user_gateway
        self.mailing_gateway = mailing_gateway
        self.id_provider = id_provider
        self.events_broker = events_broker

    async def __call__(self, data: SendMessageCommand):
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated
        current_user = await self.user_gateway.get_user_by_id(current_user_id)
        if current_user is None:
            raise UserNotFound
        # TODO role?
        if current_user.role != UserRole.ORG:
            raise AccessDenied

        user = await self.user_gateway.get_user_by_id(data.user_id)
        if user is None:
            raise UserNotFound

        await self.events_broker.publish(
            NewNotificationEvent(
                notification=NewNotificationDTO(
                    user_id=user.id,
                    title="Личное сообщение",
                    body=data.message_text,
                    type=NotificationType.MESSAGE,
                    mailing_id=None,
                ),
            )
        )

        logger.info(
            "Org %s sent message to user %s",
            current_user.id,
            user.id,
        )
