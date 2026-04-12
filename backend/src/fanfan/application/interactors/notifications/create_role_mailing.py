import logging

from pydantic import BaseModel

from fanfan.application.interactors.common.current_user import get_current_user
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.application.services.mailing import MailingService
from fanfan.core.events.notifications import NewRolesNotificationEvent
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.user import UserRole

logger = logging.getLogger(__name__)


class CreateRoleMailingInput(BaseModel):
    title: str
    body: str
    roles: list[UserRole]


class CreateRoleMailingOutput(BaseModel):
    title: str
    body: str
    roles: list[UserRole]


class CreateRoleMailing:
    def __init__(
        self,
        id_provider: IdProvider,
        user_repo: UserRepository,
        notifications_service: MailingService,
        events_broker: EventBroker,
        uow: TransactionManager,
    ):
        self.id_provider = id_provider
        self.user_repo = user_repo
        self.notifications_service = notifications_service
        self.events_broker = events_broker
        self.uow = uow

    async def __call__(self, data: CreateRoleMailingInput) -> MailingId:
        current_user = await get_current_user(
            id_provider=self.id_provider,
            user_repo=self.user_repo,
        )
        # TODO add proper permission
        if current_user.role is not UserRole.ORG:
            raise AccessDenied

        mailing = await self.notifications_service.create_new_mailing(
            total_count=0, by_user_id=current_user.id
        )
        await self.uow.commit()

        await self.events_broker.publish(
            NewRolesNotificationEvent(
                title="📣 Сообщение от организаторов",
                body=data.body,
                roles=data.roles,
                mailing_id=mailing.id,
            )
        )
        logger.info(
            "New roles mailing %s initiated by user %s",
            mailing.id,
            current_user.id,
        )
        return mailing.id
