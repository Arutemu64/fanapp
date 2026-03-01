import logging

from pydantic import BaseModel

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.nats.events_broker import EventBroker
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.events.notifications import NewRolesNotificationEvent
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.services.notifications import NotificationService
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.user import UserRole

logger = logging.getLogger(__name__)


class CreateRoleMailingCommand(BaseModel):
    title: str
    body: str
    roles: list[UserRole]


class CreateRoleMailing:
    def __init__(
        self,
        id_provider: IdProvider,
        user_gateway: UserGateway,
        notifications_service: NotificationService,
        events_broker: EventBroker,
        uow: UnitOfWork,
    ):
        self.id_provider = id_provider
        self.user_gateway = user_gateway
        self.notifications_service = notifications_service
        self.events_broker = events_broker
        self.uow = uow

    async def __call__(self, data: CreateRoleMailingCommand) -> MailingId:
        async with self.uow:
            current_user_id = await self.id_provider.get_current_user_id()
            if current_user_id is None:
                raise UserNotAuthenticated
            current_user = await self.user_gateway.get_user_by_id(current_user_id)
            if current_user is None:
                raise UserNotFound
            # TODO add proper permission
            if current_user.role is not UserRole.ORG:
                raise AccessDenied

            mailing = await self.notifications_service.create_new_mailing(
                total_notifications=0,
                by_user_id=current_user.id,
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
