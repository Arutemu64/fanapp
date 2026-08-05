from collections.abc import Callable
from uuid import UUID

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.demo.seed_demo_data import (
    DEMO_NOMINATIONS,
    DEMO_SCHEDULE,
    SeedDemoData,
)
from fanfan.application.ports.gateways import UserPermissionGateway
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.gateways.schedule_events import ScheduleEventGateway
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.schedule_event import generate_schedule_event_id
from fanfan.core.vo.user import UserId

# Seeded by the initial-data migration; the actor for CLI/scheduler/NATS work.
SYSTEM_USER_ID = UserId(UUID("00000000-0000-0000-0000-000000000000"))

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_seed_populates_schedule_and_voting(
    dishka_request: AsyncContainer,
    demo_seeder: User,
    login: Callable[[User], None],
):
    login(demo_seeder)
    interactor = await dishka_request.get(SeedDemoData)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    nomination_gateway = await dishka_request.get(NominationGateway)
    settings_gateway = await dishka_request.get(AppSettingsGateway)

    await interactor()

    schedule = await schedule_gateway.list_all()
    assert len(schedule) == len(DEMO_SCHEDULE)

    # Every seeded nomination is votable, so all of them count.
    assert await nomination_gateway.count_votable() == len(DEMO_NOMINATIONS)

    settings = await settings_gateway.get()
    assert settings.voting_enabled is True


async def test_seed_is_idempotent(
    dishka_request: AsyncContainer,
    demo_seeder: User,
    login: Callable[[User], None],
):
    # A second run must refresh the demo rows in place, not duplicate them.
    login(demo_seeder)
    interactor = await dishka_request.get(SeedDemoData)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    nomination_gateway = await dishka_request.get(NominationGateway)

    await interactor()
    await interactor()

    assert len(await schedule_gateway.list_all()) == len(DEMO_SCHEDULE)
    assert await nomination_gateway.count_votable() == len(DEMO_NOMINATIONS)


async def test_seed_leaves_an_existing_programme_untouched(
    dishka_request: AsyncContainer,
    demo_seeder: User,
    login: Callable[[User], None],
):
    # The schedule has a unique `order` column and no per-row natural key, so
    # seeding must skip a programme that already has events rather than collide.
    login(demo_seeder)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    existing = ScheduleEvent(
        id=generate_schedule_event_id(),
        number=1,
        title="Реальное выступление",
        duration=300,
        block_title="Программа",
        nomination_title=None,
        order=100.0,
        is_current=False,
        is_skipped=False,
    )
    await schedule_gateway.add(existing)

    interactor = await dishka_request.get(SeedDemoData)
    await interactor()

    schedule = await schedule_gateway.list_all()
    assert len(schedule) == 1
    assert schedule[0].title == "Реальное выступление"


async def test_seed_requires_the_permission(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    login(visitor)
    interactor = await dishka_request.get(SeedDemoData)

    with pytest.raises(AccessDenied):
        await interactor()


async def test_system_user_is_granted_demo_seed(dishka_request: AsyncContainer):
    # Guards the grant in the demo:seed migration. The `demo seed` CLI command
    # authenticates as this seeded user and goes through the same permission
    # check, so losing that user_permissions row silently breaks seeding.
    perm_gateway = await dishka_request.get(UserPermissionGateway)

    granted = await perm_gateway.get_by_permission(
        user_id=SYSTEM_USER_ID, permission=Permission.DEMO_SEED
    )

    assert granted is not None
