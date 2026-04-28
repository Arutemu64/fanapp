# ruff: noqa: S101


import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.schedule_mgmt.set_current_event import (
    SetCurrentScheduleEvent,
    SetCurrentScheduleEventInput,
)
from fanfan.application.ports.queries import ScheduleChangeQuery
from fanfan.application.ports.repositories import (
    ScheduleEventRepository,
)
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.events.schedule import CreatedScheduleChangeEvent
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.schedule_change import ScheduleChangeType
from fanfan.core.vo.schedule_event import ScheduleEventPublicNumber
from tests.mocks.event_broker import FakeEventBroker
from tests.mocks.id_provider import FakeIdProvider


@pytest.mark.asyncio
async def test_set_current_event_replaces_previous_current_and_records_change(
    dishka_request: AsyncContainer,
    schedule_manager: User,
):
    interactor = await dishka_request.get(SetCurrentScheduleEvent)
    schedule_repo = await dishka_request.get(ScheduleEventRepository)
    changes_query = await dishka_request.get(ScheduleChangeQuery)
    trx = await dishka_request.get(TransactionManager)
    events_broker = await dishka_request.get(FakeEventBroker)
    id_provider = await dishka_request.get(FakeIdProvider)
    id_provider.set_current_user_id(schedule_manager.id)

    previous_current_event = ScheduleEvent(
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
    assert change.user.id == schedule_manager.id
    assert change.user.username == schedule_manager.username
    assert change.send_global_announcement is True
    assert change.mailing_id is not None

    assert events_broker.published_events == [
        CreatedScheduleChangeEvent(schedule_change_id=change.id)
    ]
