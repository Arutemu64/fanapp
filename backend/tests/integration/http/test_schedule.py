from collections.abc import Awaitable, Callable
from http import HTTPStatus

from dishka import AsyncContainer
from httpx2 import AsyncClient

from fanfan.application.ports.gateways import ScheduleEntryGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.schedule_entry import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.schedule_entry import generate_schedule_entry_id


async def _add_event(dishka_request: AsyncContainer) -> ScheduleEvent:
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    uow = await dishka_request.get(UnitOfWork)
    event = ScheduleEvent(
        id=generate_schedule_entry_id(),
        number=1,
        title="Открытие фестиваля",
        duration_seconds=600,
        order=1,
        is_current=False,
        is_skipped=False,
        nomination_title=None,
    )
    await schedule_gateway.add(event)
    await uow.commit()
    return event


async def test_cached_schedule_revalidates_until_an_organizer_changes_it(
    dishka_request: AsyncContainer,
    client: AsyncClient,
    schedule_editor: User,
    sign_in: Callable[[User], Awaitable[None]],
) -> None:
    event = await _add_event(dishka_request)

    first = await client.get("/schedule")
    assert first.status_code == HTTPStatus.OK
    assert first.headers["cache-control"] == "no-cache"
    etag = first.headers["etag"]

    unchanged = await client.get("/schedule", headers={"If-None-Match": etag})
    assert unchanged.status_code == HTTPStatus.NOT_MODIFIED
    assert unchanged.content == b""

    await sign_in(schedule_editor)
    moved = await client.put("/schedule/current", json={"event_id": str(event.id)})
    assert moved.status_code == HTTPStatus.NO_CONTENT

    changed = await client.get("/schedule", headers={"If-None-Match": etag})
    assert changed.status_code == HTTPStatus.OK
    assert changed.headers["etag"] != etag


async def test_responses_carry_the_security_headers(client: AsyncClient) -> None:
    response = await client.get("/schedule")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
