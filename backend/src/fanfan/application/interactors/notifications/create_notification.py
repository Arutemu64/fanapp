from pydantic import BaseModel

from fanfan.application.services.notification_fan_out import NotificationFanOut
from fanfan.core.models.notification import NewNotification


class CreateNotificationInput(BaseModel):
    notification: NewNotification


class CreateNotification:
    """Handles one CreateNotificationCommand: a fan-out of a single recipient."""

    def __init__(self, fan_out: NotificationFanOut) -> None:
        self.fan_out = fan_out

    async def __call__(self, data: CreateNotificationInput) -> None:
        await self.fan_out([data.notification])
