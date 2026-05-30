import logging
from dataclasses import dataclass

from fanfan.application.dto.notification import NewNotificationDTO
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.repositories.mailings import MailingRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.events.notifications import NewNotificationEvent
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.vo.notification import NotificationType, generate_notification_id
from fanfan.core.vo.user import UserId, UserRole

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class SendMessageInput:
    user_id: UserId
    message_text: str


class SendMessage:
    def __init__(
        self,
        user_repo: UserRepository,
        mailing_repo: MailingRepository,
        current_user_provider: CurrentUserProvider,
        events_broker: EventBroker,
    ):
        self.user_repo = user_repo
        self.mailing_repo = mailing_repo
        self.current_user_provider = current_user_provider
        self.events_broker = events_broker

    async def __call__(self, data: SendMessageInput):
        current_user = await self.current_user_provider.require_user()
        # TODO proper permission
        if current_user.role != UserRole.ORG:
            raise AccessDenied

        user = await self.user_repo.get_by_id(data.user_id)
        if user is None:
            raise UserNotFound

        await self.events_broker.publish(
            NewNotificationEvent(
                notification=NewNotificationDTO(
                    id=generate_notification_id(),
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
