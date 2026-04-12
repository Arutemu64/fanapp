import logging
from dataclasses import dataclass

from fanfan.application.dto.notification import NewNotificationDTO
from fanfan.application.interactors.common.current_user import get_current_user
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.mailings import MailingRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.core.events.notifications import NewNotificationEvent
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.vo.notification import NotificationType
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
        id_provider: IdProvider,
        events_broker: EventBroker,
    ):
        self.user_repo = user_repo
        self.mailing_repo = mailing_repo
        self.id_provider = id_provider
        self.events_broker = events_broker

    async def __call__(self, data: SendMessageInput):
        current_user = await get_current_user(
            id_provider=self.id_provider,
            user_repo=self.user_repo,
        )
        # TODO proper permission
        if current_user.role != UserRole.ORG:
            raise AccessDenied

        user = await self.user_repo.get_by_id(data.user_id)
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
