from pydantic import BaseModel

from fanfan.application.dto.notification import RealtimeNotificationDTO
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.core.exceptions.notifications import NotificationNotFound
from fanfan.core.vo.notification import NotificationId


class GetNotificationInput(BaseModel):
    notification_id: NotificationId


class GetNotification:
    def __init__(self, notification_gateway: NotificationGateway):
        self.notification_gateway = notification_gateway

    async def __call__(self, data: GetNotificationInput) -> RealtimeNotificationDTO:
        notification = await self.notification_gateway.read_realtime_notification(
            data.notification_id
        )
        if notification is None:
            raise NotificationNotFound

        return notification
