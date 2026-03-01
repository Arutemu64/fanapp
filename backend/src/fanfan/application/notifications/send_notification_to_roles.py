from dataclasses import dataclass

from fanfan.adapters.db.gateways.mailings import MailingGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.nats.events_broker import EventBroker
from fanfan.core.dto.notification import NewNotificationDTO
from fanfan.core.events.notifications import NewNotificationEvent
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.user import UserRole


@dataclass(slots=True, frozen=True)
class SendNotificationToRolesDTO:
    title: str
    body: str
    roles: list[UserRole]
    mailing_id: MailingId


class SendNotificationToRoles:
    def __init__(
        self,
        user_gateway: UserGateway,
        events_broker: EventBroker,
        mailing_gateway: MailingGateway,
        uow: UnitOfWork,
    ):
        self.user_gateway = user_gateway
        self.events_broker = events_broker
        self.mailing_gateway = mailing_gateway
        self.uow = uow

    async def __call__(self, data: SendNotificationToRolesDTO):
        async with self.uow:
            users = await self.user_gateway.read_all_by_roles(*data.roles)
            mailing = await self.mailing_gateway.get_mailing(data.mailing_id, lock=True)
            mailing.update_total(len(users))
            await self.mailing_gateway.save_mailing(mailing)
            await self.uow.commit()

            events = [
                NewNotificationEvent(
                    notification=NewNotificationDTO(
                        user_id=u.id,
                        title=data.title,
                        body=data.body,
                        mailing_id=data.mailing_id,
                    )
                )
                for u in users
            ]
            for e in events:
                await self.events_broker.publish(e)
