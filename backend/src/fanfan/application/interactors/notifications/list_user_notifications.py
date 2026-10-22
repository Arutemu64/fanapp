from pydantic import BaseModel

from fanfan.application.dto.notification import NotificationDTO
from fanfan.application.dto.page import CursorPagination, cut_page
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.services.current_user import CurrentUserProvider


class ListUserNotificationsInput(BaseModel):
    pagination: CursorPagination


class ListUserNotificationsOutput(BaseModel):
    notifications: list[NotificationDTO]
    next_cursor: str | None


class ListUserNotifications:
    def __init__(
        self,
        notification_gateway: NotificationGateway,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.notification_gateway = notification_gateway
        self.current_user_provider = current_user_provider

    async def __call__(
        self, data: ListUserNotificationsInput
    ) -> ListUserNotificationsOutput:
        current_user_id = await self.current_user_provider.require_user_id()

        rows = await self.notification_gateway.read_list_user_notifications(
            user_id=current_user_id,
            pagination=data.pagination,
        )
        notifications, next_cursor = cut_page(rows, data.pagination)
        return ListUserNotificationsOutput(
            notifications=notifications, next_cursor=next_cursor
        )
