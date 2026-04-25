from pydantic import BaseModel

from fanfan.application.dto.notification import RealtimeNotificationDTO
from fanfan.application.ports.queries.notifications import NotificationQuery
from fanfan.core.exceptions.notifications import NotificationNotFound
from fanfan.core.vo.notification import NotificationId


class GetNotificationInput(BaseModel):
    notification_id: NotificationId


class GetNotification:
    def __init__(self, notification_query: NotificationQuery):
        self.notification_query = notification_query

    async def __call__(self, data: GetNotificationInput) -> RealtimeNotificationDTO:
        notification = await self.notification_query.read_realtime_notification(
            data.notification_id
        )
        if notification is None:
            raise NotificationNotFound

        return notification
