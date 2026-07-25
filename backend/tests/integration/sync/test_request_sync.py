from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from dishka import AsyncContainer
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import SyncRunORM
from fanfan.application.interactors.sync.request_sync import (
    RequestSync,
    RequestSyncInput,
)
from fanfan.application.ports.gateways.outbox import OutboxGateway
from fanfan.application.ports.gateways.sync_runs import SyncRunGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.sync_run_tracker import (
    STALE_RUN_ERROR,
    STALE_RUN_TIMEOUT,
)
from fanfan.core.events.sync import SyncRequested
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.sync import SyncAlreadyRunning
from fanfan.core.models.sync_run import SyncRun
from fanfan.core.models.user import User
from fanfan.core.vo.sync import SyncRunStatus, SyncSource
from tests.integration.conftest import as_outbox

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_request_sync_creates_pending_run_and_enqueues_event(
    dishka_request: AsyncContainer,
    sync_operator: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
):
    login(sync_operator)
    interactor = await dishka_request.get(RequestSync)

    run = await interactor(RequestSyncInput(source=SyncSource.COSPLAY2))

    assert run.source is SyncSource.COSPLAY2
    assert run.status is SyncRunStatus.PENDING
    assert run.finished_at is None
    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(SyncRequested(sync_run_id=run.id, source=SyncSource.COSPLAY2))


async def test_request_sync_records_the_requesting_organizer(
    dishka_request: AsyncContainer,
    sync_operator: User,
    login: Callable[[User], None],
):
    login(sync_operator)
    interactor = await dishka_request.get(RequestSync)
    gateway = await dishka_request.get(SyncRunGateway)

    dto = await interactor(RequestSyncInput(source=SyncSource.TCLOUD))

    stored = await gateway.get(dto.id)
    assert stored is not None
    assert stored.by_user_id == sync_operator.id


async def test_request_sync_requires_the_permission(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    login(visitor)
    interactor = await dishka_request.get(RequestSync)

    with pytest.raises(AccessDenied):
        await interactor(RequestSyncInput(source=SyncSource.COSPLAY2))


async def test_request_sync_rejects_a_second_run_for_the_same_source(
    dishka_request: AsyncContainer,
    sync_operator: User,
    login: Callable[[User], None],
):
    login(sync_operator)
    interactor = await dishka_request.get(RequestSync)

    await interactor(RequestSyncInput(source=SyncSource.COSPLAY2))

    with pytest.raises(SyncAlreadyRunning):
        await interactor(RequestSyncInput(source=SyncSource.COSPLAY2))


async def test_request_sync_reaps_a_wedged_run_instead_of_blocking_forever(
    dishka_request: AsyncContainer,
    sync_operator: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    # A worker killed mid-run leaves an active row behind. Without reaping, the
    # partial unique index would reject every future run for that source.
    login(sync_operator)
    gateway = await dishka_request.get(SyncRunGateway)
    wedged = SyncRun.create(source=SyncSource.COSPLAY2, by_user_id=sync_operator.id)
    await gateway.add(wedged)
    await uow.commit()
    await _age_run(dishka_request, wedged)

    interactor = await dishka_request.get(RequestSync)
    fresh = await interactor(RequestSyncInput(source=SyncSource.COSPLAY2))

    assert fresh.status is SyncRunStatus.PENDING
    reaped = await gateway.get(wedged.id)
    assert reaped is not None
    assert reaped.status is SyncRunStatus.FAILED
    assert reaped.error == STALE_RUN_ERROR


async def _age_run(dishka_request: AsyncContainer, run: SyncRun) -> None:
    """Backdate a run's created_at past the stale timeout."""
    session = await dishka_request.get(AsyncSession)
    await session.execute(
        update(SyncRunORM)
        .where(SyncRunORM.id == run.id)
        .values(created_at=datetime.now(UTC) - STALE_RUN_TIMEOUT * 2)
    )
