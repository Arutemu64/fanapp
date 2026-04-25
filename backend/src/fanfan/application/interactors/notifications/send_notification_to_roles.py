from pydantic import BaseModel

from fanfan.application.dto.notification import NewNotificationDTO
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.queries.users import UserQuery
from fanfan.application.ports.repositories.mailings import MailingRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.events.notifications import NewNotificationEvent
from fanfan.core.exceptions.notifications import MailingNotFound
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationType
from fanfan.core.vo.user import UserRole


class SendNotificationToRolesInput(BaseModel):
    title: str
    body: str
    roles: list[UserRole]
    mailing_id: MailingId


class SendNotificationToRoles:
    def __init__(
        self,
        user_query: UserQuery,
        events_broker: EventBroker,
        mailing_repo: MailingRepository,
        trx: TransactionManager,
    ):
        self.user_query = user_query
        self.events_broker = events_broker
        self.mailing_repo = mailing_repo
        self.trx = trx

    async def __call__(self, data: SendNotificationToRolesInput):
        users = await self.user_query.read_all_by_roles(*data.roles)
        mailing = await self.mailing_repo.get(data.mailing_id)
        if mailing is None:
            raise MailingNotFound
        mailing.update_total(len(users))
        await self.mailing_repo.save(mailing)
        await self.trx.commit()

        events = [
            NewNotificationEvent(
                notification=NewNotificationDTO(
                    user_id=u.id,
                    title=data.title,
                    body=data.body,
                    mailing_id=data.mailing_id,
                    type=NotificationType.DEFAULT,
                )
            )
            for u in users
        ]
        for e in events:
            await self.events_broker.publish(e)
