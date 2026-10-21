import importlib
import pkgutil

import pytest

import fanfan.core.events
from fanfan.core.events.base import AppEvent
from fanfan.core.events.notifications import NotificationCreated
from fanfan.core.vo.notification import generate_notification_id
from fanfan.presentation.worker.routes import setup_router

pytestmark = pytest.mark.unit


def _all_event_types() -> list[type[AppEvent]]:
    # Import every events module first: a subclass is only registered once its
    # module has been imported, and nothing else guarantees that here.
    for module in pkgutil.iter_modules(fanfan.core.events.__path__):
        importlib.import_module(f"{fanfan.core.events.__name__}.{module.name}")
    found: list[type[AppEvent]] = []
    pending = list(AppEvent.__subclasses__())
    while pending:
        event_type = pending.pop()
        pending.extend(event_type.__subclasses__())
        # Tests define throwaway AppEvent subclasses; only the app's own count.
        if event_type.__module__.startswith("fanfan."):
            found.append(event_type)
    return found


def test_every_event_has_a_job_handler() -> None:
    # The UnitOfWork raises on an event no handler takes, rolling back the write
    # that recorded it. Catch an unhandled event here rather than as a 500.
    routes = setup_router().routes()
    orphaned = [
        f"{event_type.__name__} ({event_type.subject})"
        for event_type in _all_event_types()
        if event_type.subject not in routes.jobs_by_subject
    ]

    assert orphaned == [], f"Events with no job handler: {orphaned}"


def test_an_event_starts_one_job_per_handler() -> None:
    routes = setup_router().routes()

    jobs = routes.jobs_for(
        NotificationCreated(notification_id=generate_notification_id())
    )

    assert set(jobs) == {
        "send_notification_to_telegram",
        "send_notification_to_vk",
        "send_push_notification",
    }
