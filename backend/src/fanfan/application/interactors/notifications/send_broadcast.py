import logging

from pydantic import BaseModel

from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.events.notifications import BroadcastQueued
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.mailing import Mailing
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.user import UserRole

logger = logging.getLogger(__name__)


class SendBroadcastInput(BaseModel):
    body: str
    roles: list[UserRole]


class SendBroadcastOutput(BaseModel):
    mailing_id: MailingId


class SendBroadcast:
    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        user_repo: UserGateway,
        mailing_repo: MailingGateway,
        events_broker: EventBroker,
        uow: UnitOfWork,
    ):
        self.current_user_provider = current_user_provider
        self.user_repo = user_repo
        self.mailing_repo = mailing_repo
        self.events_broker = events_broker
        self.uow = uow

    async def __call__(self, data: SendBroadcastInput) -> SendBroadcastOutput:
        current_user = await self.current_user_provider.require_user()
        # TODO add proper permission
        if current_user.role is not UserRole.ORG:
            raise AccessDenied

        mailing = Mailing.create(by_user_id=current_user.id)
        await self.mailing_repo.add(mailing)
        await self.uow.commit()

        await self.events_broker.publish(
            BroadcastQueued(
                mailing_id=mailing.id,
                body=data.body,
                roles=data.roles,
            )
        )
        logger.info(
            "New broadcast %s initiated by user %s",
            mailing.id,
            current_user.id,
        )
        return SendBroadcastOutput(mailing_id=mailing.id)
