from uuid import UUID

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.schedule_mgmt.set_current_schedule_event import (
    SetCurrentScheduleEvent,
    SetCurrentScheduleEventInput,
)
from fanfan.application.ports.queries import ScheduleChangeQuery
from fanfan.application.ports.repositories import (
    ScheduleEventRepository,
)
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.events.schedule import ScheduleChangeCreated
from fanfan.core.exceptions.schedule import EventNotFound
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.schedule_change import ScheduleChangeType
from fanfan.core.vo.schedule_event import (
    ScheduleEventId,
    ScheduleEventPublicNumber,
    generate_schedule_event_id,
)
from tests.fakes.event_broker import FakeEventBroker
from tests.fakes.id_provider import FakeIdProvider

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


def _schedule_event(
    public_number: int,
    title: str,
    order: float,
    *,
    is_current: bool = False,
) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_event_id(),
        public_number=ScheduleEventPublicNumber(public_number),
        title=title,
        duration=15,
        order=order,
        is_current=is_current,
        is_skipped=False,
        nomination_title=None,
        block_title=None,
    )


async def test_set_current_event_replaces_previous_current_and_records_change(
    dishka_request: AsyncContainer,
    schedule_editor: User,
):
    interactor = await dishka_request.get(SetCurrentScheduleEvent)
    schedule_repo = await dishka_request.get(ScheduleEventRepository)
    changes_query = await dishka_request.get(ScheduleChangeQuery)
    trx = await dishka_request.get(TransactionManager)
    events_broker = await dishka_request.get(FakeEventBroker)
    id_provider = await dishka_request.get(FakeIdProvider)
    id_provider.set_current_user_id(schedule_editor.id)

    previous_current_event = ScheduleEvent(
        id=generate_schedule_event_id(),
        public_number=ScheduleEventPublicNumber(1),
        title="Старое текущее событие",
        duration=15,
        order=1,
        is_current=True,
        is_skipped=False,
        nomination_title=None,
        block_title=None,
    )
    new_current_event = ScheduleEvent(
        id=generate_schedule_event_id(),
        public_number=ScheduleEventPublicNumber(2),
        title="Новое текущее событие",
        duration=20,
        order=2,
        is_current=False,
        is_skipped=False,
        nomination_title="Номинация",
        block_title="Блок",
    )
    await schedule_repo.add(previous_current_event)
    await schedule_repo.add(new_current_event)
    await trx.commit()

    await interactor(SetCurrentScheduleEventInput(event_id=new_current_event.id))

    saved_previous_event = await schedule_repo.get_by_id(previous_current_event.id)
    saved_new_event = await schedule_repo.get_by_id(new_current_event.id)
    assert saved_previous_event is not None
    assert saved_new_event is not None
    assert saved_previous_event.is_current is False
    assert saved_new_event.is_current is True

    changes = await changes_query.read_list_schedule_changes()
    assert len(changes) == 1
    change = changes[0]
    assert change.type == ScheduleChangeType.SET_AS_CURRENT
    assert change.changed_event is not None
    assert change.changed_event.id == new_current_event.id
    assert change.argument_event is not None
    assert change.argument_event.id == previous_current_event.id
    assert change.user is not None
    assert change.user.id == schedule_editor.id
    assert change.user.username == schedule_editor.username
    assert change.next_event_changed is True
    assert change.mailing_id is not None

    assert events_broker.published_events == [
        ScheduleChangeCreated(schedule_change_id=change.id)
    ]


async def test_set_current_event_can_unset_current_event(
    dishka_request: AsyncContainer,
    schedule_editor: User,
):
    interactor = await dishka_request.get(SetCurrentScheduleEvent)
    schedule_repo = await dishka_request.get(ScheduleEventRepository)
    changes_query = await dishka_request.get(ScheduleChangeQuery)
    trx = await dishka_request.get(TransactionManager)
    events_broker = await dishka_request.get(FakeEventBroker)
    id_provider = await dishka_request.get(FakeIdProvider)
    id_provider.set_current_user_id(schedule_editor.id)

    previous_current_event = _schedule_event(1, "Текущее событие", 1, is_current=True)
    await schedule_repo.add(previous_current_event)
    await trx.commit()

    await interactor(SetCurrentScheduleEventInput(event_id=None))

    saved_previous_event = await schedule_repo.get_by_id(previous_current_event.id)
    assert saved_previous_event is not None
    assert saved_previous_event.is_current is False

    changes = await changes_query.read_list_schedule_changes()
    assert len(changes) == 1
    change = changes[0]
    assert change.type == ScheduleChangeType.SET_AS_CURRENT
    assert change.changed_event is None
    assert change.argument_event is not None
    assert change.argument_event.id == previous_current_event.id
    assert change.user is not None
    assert change.user.id == schedule_editor.id
    assert change.next_event_changed is True
    assert change.mailing_id is not None

    assert events_broker.published_events == [
        ScheduleChangeCreated(schedule_change_id=change.id)
    ]


async def test_set_current_event_raises_when_event_not_found(
    dishka_request: AsyncContainer,
    schedule_editor: User,
):
    interactor = await dishka_request.get(SetCurrentScheduleEvent)
    schedule_repo = await dishka_request.get(ScheduleEventRepository)
    changes_query = await dishka_request.get(ScheduleChangeQuery)
    trx = await dishka_request.get(TransactionManager)
    events_broker = await dishka_request.get(FakeEventBroker)
    id_provider = await dishka_request.get(FakeIdProvider)
    id_provider.set_current_user_id(schedule_editor.id)

    previous_current_event = _schedule_event(1, "Текущее событие", 1, is_current=True)
    await schedule_repo.add(previous_current_event)
    await trx.commit()

    unknown_event_id = ScheduleEventId(UUID("00000000-0000-0000-0000-000000000000"))

    with pytest.raises(EventNotFound):
        await interactor(SetCurrentScheduleEventInput(event_id=unknown_event_id))

    # Откатываем сброшенный current из незавершённой транзакции после ошибки.
    await trx.rollback()

    saved_previous_event = await schedule_repo.get_by_id(previous_current_event.id)
    assert saved_previous_event is not None
    assert saved_previous_event.is_current is True
    assert await changes_query.read_list_schedule_changes() == []
    assert events_broker.published_events == []
