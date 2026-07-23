from collections.abc import AsyncIterator

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.tickets.sync_tickets import SyncTickets
from fanfan.application.ports.gateways.sync_runs import SyncRunGateway
from fanfan.application.ports.sources.tickets import ExternalTicket
from fanfan.core.vo.sync import SyncRunStatus, SyncSource, SyncTrigger
from fanfan.core.vo.user import UserRole
from tests.fakes.tickets_source import FakeTicketsSource

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_sync_records_completed_run(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(SyncTickets)
    source = await dishka_request.get(FakeTicketsSource)
    sync_run_gateway = await dishka_request.get(SyncRunGateway)

    source.tickets = [
        ExternalTicket(external_id="ext-1", barcode="barcode-1", role=UserRole.VISITOR)
    ]

    await interactor()

    runs = await sync_run_gateway.read_recent_runs(SyncSource.TICKETSCLOUD, limit=10)
    assert len(runs) == 1
    run = runs[0]
    assert run.status is SyncRunStatus.COMPLETED
    assert run.trigger is SyncTrigger.SCHEDULE
    assert run.error_message is None
    # System-triggered runs carry no user; the trigger attributes them.
    assert run.started_by is None
    assert run.finished_at >= run.started_at

    last_success = await sync_run_gateway.read_last_completed_at(
        SyncSource.TICKETSCLOUD
    )
    assert last_success == run.finished_at


async def test_sync_records_failed_run_and_keeps_no_partial_state(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(SyncTickets)
    source = await dishka_request.get(FakeTicketsSource)
    sync_run_gateway = await dishka_request.get(SyncRunGateway)

    async def broken_fetch() -> AsyncIterator[ExternalTicket]:
        msg = "vendor down"
        raise RuntimeError(msg)
        yield  # pragma: no cover - makes this an async generator

    source.fetch_all_tickets = broken_fetch  # type: ignore[method-assign]

    with pytest.raises(RuntimeError):
        await interactor(trigger=SyncTrigger.CLI)

    runs = await sync_run_gateway.read_recent_runs(SyncSource.TICKETSCLOUD, limit=10)
    assert len(runs) == 1
    run = runs[0]
    assert run.status is SyncRunStatus.FAILED
    assert run.trigger is SyncTrigger.CLI
    assert run.error_message == "vendor down"

    # A failed run must not move the "last synced" timestamp.
    assert (
        await sync_run_gateway.read_last_completed_at(SyncSource.TICKETSCLOUD) is None
    )
