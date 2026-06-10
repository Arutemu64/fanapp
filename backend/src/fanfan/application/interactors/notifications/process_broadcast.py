from pydantic import BaseModel

from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.queries.users import UserQuery
from fanfan.application.ports.repositories.mailings import MailingRepository
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.notifications import NotificationQueued
from fanfan.core.exceptions.notifications import MailingNotFound
from fanfan.core.models.notification import NewNotification
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationType, generate_notification_id
from fanfan.core.vo.user import UserRole


class ProcessBroadcastInput(BaseModel):
    mailing_id: MailingId
    body: str
    roles: list[UserRole]


class ProcessBroadcast:
    def __init__(
        self,
        user_query: UserQuery,
        events_broker: EventBroker,
        mailing_repo: MailingRepository,
        uow: UnitOfWork,
    ):
        self.user_query = user_query
        self.events_broker = events_broker
        self.mailing_repo = mailing_repo
        self.uow = uow

    async def __call__(self, data: ProcessBroadcastInput):
        users = await self.user_query.read_all_by_roles(*data.roles)
        mailing = await self.mailing_repo.get(data.mailing_id)
        if mailing is None:
            raise MailingNotFound
        await self.mailing_repo.set_total(mailing_id=mailing.id, total_count=len(users))
        await self.mailing_repo.save(mailing)
        await self.uow.commit()

        events = [
            NotificationQueued(
                notification=NewNotification(
                    id=generate_notification_id(),
                    user_id=u.id,
                    title="Рассылка от организаторов",
                    body=data.body,
                    mailing_id=data.mailing_id,
                    type=NotificationType.BROADCAST,
                )
            )
            for u in users
        ]
        for e in events:
            await self.events_broker.publish(e)
