from dishka import AsyncContainer

from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.core.events.notifications import NotificationCreated
from fanfan.core.models.notification import Notification
from tests.fakes.event_broker import FakeEventBroker


async def delivered_notifications(dishka_request: AsyncContainer) -> list[Notification]:
    """The stored notifications a fan-out handed to the channels, in order."""
    broker = await dishka_request.get(FakeEventBroker)
    gateway = await dishka_request.get(NotificationGateway)
    notifications: list[Notification] = []
    for event in broker.published_events:
        if not isinstance(event, NotificationCreated):
            continue
        notification = await gateway.get(event.notification_id, lock=False)
        assert notification is not None, "handed over but never stored"
        notifications.append(notification)
    return notifications
