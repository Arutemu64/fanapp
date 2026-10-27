from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

import pytest
from dishka import AsyncContainer
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from fanfan.adapters.db.models import SyncRunORM
from fanfan.adapters.db.worker_lock import PostgresWorkerLock
from fanfan.application.interactors.sync.execute_cosplay_sync import ExecuteCosplaySync
from fanfan.application.ports.gateways import UserPermissionGateway
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.gateways.sync_runs import SyncRunGateway
from fanfan.application.ports.sources.cosplay import ExternalNomination
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.sync_run_tracker import (
    STALE_RUN_TIMEOUT,
    sync_lock_key,
)
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.sync import SyncAlreadyRunning
from fanfan.core.models.nomination import Nomination
from fanfan.core.models.sync_run import SyncRun
from fanfan.core.models.user import User
from fanfan.core.vo.nomination import generate_nomination_id
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.sync import SyncRunStatus, SyncSource
from fanfan.core.vo.user import UserId
from tests.fakes.cosplay_source import FakeCosplaySource

SYSTEM_USER_ID = UserId(UUID("00000000-0000-0000-0000-000000000000"))

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_unattended_run_is_recorded_and_attributed(
    dishka_request: AsyncContainer,
    sync_operator: User,
    login: Callable[[User], None],
) -> None:
    login(sync_operator)
    source = await dishka_request.get(FakeCosplaySource)
    source.nominations = [ExternalNomination(external_id=1, code="c1", title="Косплей")]
    interactor = await dishka_request.get(ExecuteCosplaySync)
    gateway = await dishka_request.get(SyncRunGateway)

    await interactor()

    latest = await gateway.read_latest_by_source()
    run = latest[SyncSource.COSPLAY2]
    assert run.status is SyncRunStatus.FINISHED
    assert run.started_at is not None
    assert run.finished_at is not None
    assert run.result is not None

    stored = await gateway.get(run.id)
    assert stored is not None
    assert stored.by_user_id == sync_operator.id


async def test_run_id_adopts_the_existing_pending_row(
    dishka_request: AsyncContainer,
    sync_operator: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    login(sync_operator)
    gateway = await dishka_request.get(SyncRunGateway)
    queued = SyncRun.create(source=SyncSource.COSPLAY2, by_user_id=sync_operator.id)
    await gateway.add(queued)
    await uow.commit()

    interactor = await dishka_request.get(ExecuteCosplaySync)
    await interactor(run_id=queued.id)

    adopted = await gateway.get(queued.id)
    assert adopted is not None
    assert adopted.status is SyncRunStatus.FINISHED
    latest = await gateway.read_latest_by_source()
    assert latest[SyncSource.COSPLAY2].id == queued.id


async def test_redelivered_trigger_does_not_rerun_a_finished_run(
    dishka_request: AsyncContainer,
    sync_operator: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    login(sync_operator)
    source = await dishka_request.get(FakeCosplaySource)
    gateway = await dishka_request.get(SyncRunGateway)
    queued = SyncRun.create(source=SyncSource.COSPLAY2, by_user_id=sync_operator.id)
    await gateway.add(queued)
    await uow.commit()
    interactor = await dishka_request.get(ExecuteCosplaySync)
    await interactor(run_id=queued.id)
    finished = await gateway.get(queued.id)
    assert finished is not None
    first_finished_at = finished.finished_at
    await uow.commit()

    source.nominations = [ExternalNomination(external_id=1, code="c1", title="Косплей")]
    await interactor(run_id=queued.id)

    rerun = await gateway.get(queued.id)
    assert rerun is not None
    assert rerun.status is SyncRunStatus.FINISHED
    assert rerun.finished_at == first_finished_at
    nominations = await dishka_request.get(NominationGateway)
    assert await nominations.get_by_cosplay2_id(1) is None


async def test_redelivered_trigger_resumes_an_interrupted_run(
    dishka_request: AsyncContainer,
    sync_operator: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    login(sync_operator)
    source = await dishka_request.get(FakeCosplaySource)
    source.nominations = [ExternalNomination(external_id=1, code="c1", title="Косплей")]
    gateway = await dishka_request.get(SyncRunGateway)
    interrupted = SyncRun.create(
        source=SyncSource.COSPLAY2, by_user_id=sync_operator.id
    )
    interrupted.mark_running(datetime.now(UTC))
    await gateway.add(interrupted)
    await uow.commit()

    interactor = await dishka_request.get(ExecuteCosplaySync)
    await interactor(run_id=interrupted.id)

    resumed = await gateway.get(interrupted.id)
    assert resumed is not None
    assert resumed.status is SyncRunStatus.FINISHED
    nominations = await dishka_request.get(NominationGateway)
    assert await nominations.get_by_cosplay2_id(1) is not None


async def test_redelivered_trigger_backs_off_while_a_live_worker_holds_the_run(
    dishka_request: AsyncContainer,
    sync_operator: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    login(sync_operator)
    source = await dishka_request.get(FakeCosplaySource)
    source.nominations = [ExternalNomination(external_id=1, code="c1", title="Косплей")]
    gateway = await dishka_request.get(SyncRunGateway)
    running = SyncRun.create(source=SyncSource.COSPLAY2, by_user_id=sync_operator.id)
    running.mark_running(datetime.now(UTC))
    await gateway.add(running)
    await uow.commit()
    live_worker = PostgresWorkerLock(await dishka_request.get(AsyncEngine))
    assert await live_worker.try_acquire(sync_lock_key(SyncSource.COSPLAY2))

    interactor = await dishka_request.get(ExecuteCosplaySync)
    try:
        with pytest.raises(SyncAlreadyRunning):
            await interactor(run_id=running.id)
        nominations = await dishka_request.get(NominationGateway)
        assert await nominations.get_by_cosplay2_id(1) is None
    finally:
        await live_worker.release()


async def test_unattended_run_skips_quietly_when_one_is_active(
    dishka_request: AsyncContainer,
    sync_operator: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    login(sync_operator)
    gateway = await dishka_request.get(SyncRunGateway)
    active = SyncRun.create(source=SyncSource.COSPLAY2, by_user_id=sync_operator.id)
    await gateway.add(active)
    await uow.commit()

    interactor = await dishka_request.get(ExecuteCosplaySync)
    await interactor()

    untouched = await gateway.get(active.id)
    assert untouched is not None
    assert untouched.status is SyncRunStatus.PENDING


async def test_unattended_run_reaps_a_wedged_run_and_proceeds(
    dishka_request: AsyncContainer,
    sync_operator: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    login(sync_operator)
    gateway = await dishka_request.get(SyncRunGateway)
    wedged = SyncRun.create(source=SyncSource.COSPLAY2, by_user_id=sync_operator.id)
    await gateway.add(wedged)
    await uow.commit()
    session = await dishka_request.get(AsyncSession)
    await session.execute(
        update(SyncRunORM)
        .where(SyncRunORM.id == wedged.id)
        .values(created_at=datetime.now(UTC) - STALE_RUN_TIMEOUT * 2)
    )

    interactor = await dishka_request.get(ExecuteCosplaySync)
    await interactor()

    reaped = await gateway.get(wedged.id)
    assert reaped is not None
    assert reaped.status is SyncRunStatus.FAILED
    latest = await gateway.read_latest_by_source()
    assert latest[SyncSource.COSPLAY2].status is SyncRunStatus.FINISHED


async def test_unattended_run_spares_a_long_run_whose_worker_is_alive(
    dishka_request: AsyncContainer,
    sync_operator: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    login(sync_operator)
    gateway = await dishka_request.get(SyncRunGateway)
    running = SyncRun.create(source=SyncSource.COSPLAY2, by_user_id=sync_operator.id)
    running.mark_running(datetime.now(UTC))
    await gateway.add(running)
    await uow.commit()
    session = await dishka_request.get(AsyncSession)
    await session.execute(
        update(SyncRunORM)
        .where(SyncRunORM.id == running.id)
        .values(created_at=datetime.now(UTC) - STALE_RUN_TIMEOUT * 2)
    )
    live_worker = PostgresWorkerLock(await dishka_request.get(AsyncEngine))
    assert await live_worker.try_acquire(sync_lock_key(SyncSource.COSPLAY2))

    interactor = await dishka_request.get(ExecuteCosplaySync)
    try:
        await interactor()
    finally:
        await live_worker.release()

    untouched = await gateway.get(running.id)
    assert untouched is not None
    assert untouched.status is SyncRunStatus.RUNNING


async def test_vendor_failure_is_recorded_not_raised(
    dishka_request: AsyncContainer,
    sync_operator: User,
    login: Callable[[User], None],
) -> None:
    login(sync_operator)
    source = await dishka_request.get(FakeCosplaySource)
    source.raises = RuntimeError("cosplay2 is down")
    interactor = await dishka_request.get(ExecuteCosplaySync)
    gateway = await dishka_request.get(SyncRunGateway)

    await interactor()

    run = (await gateway.read_latest_by_source())[SyncSource.COSPLAY2]
    assert run.status is SyncRunStatus.FAILED
    assert run.error is not None
    assert run.finished_at is not None


async def test_failure_mid_flush_is_recorded_not_left_running(
    dishka_request: AsyncContainer,
    sync_operator: User,
    login: Callable[[User], None],
) -> None:
    login(sync_operator)
    source = await dishka_request.get(FakeCosplaySource)
    source.nominations = [
        ExternalNomination(external_id=1, code="dup", title="Первая"),
        ExternalNomination(external_id=2, code="dup", title="Вторая"),
    ]
    interactor = await dishka_request.get(ExecuteCosplaySync)
    gateway = await dishka_request.get(SyncRunGateway)

    await interactor()

    run = (await gateway.read_latest_by_source())[SyncSource.COSPLAY2]
    assert run.status is SyncRunStatus.FAILED
    assert run.error is not None
    assert run.finished_at is not None


async def test_recreated_nomination_may_reuse_a_retired_code(
    dishka_request: AsyncContainer,
    sync_operator: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    login(sync_operator)
    nomination_gateway = await dishka_request.get(NominationGateway)
    await nomination_gateway.add(
        Nomination(
            id=generate_nomination_id(),
            cosplay2_id=100,
            code="sv",
            title="Старая номинация",
            is_votable=False,
        )
    )
    await uow.commit()

    source = await dishka_request.get(FakeCosplaySource)
    source.nominations = [ExternalNomination(external_id=200, code="sv", title="Новая")]
    interactor = await dishka_request.get(ExecuteCosplaySync)
    sync_run_gateway = await dishka_request.get(SyncRunGateway)

    await interactor()

    run = (await sync_run_gateway.read_latest_by_source())[SyncSource.COSPLAY2]
    assert run.status is SyncRunStatus.FINISHED
    assert await nomination_gateway.get_by_cosplay2_id(100) is None
    migrated = await nomination_gateway.get_by_cosplay2_id(200)
    assert migrated is not None
    assert migrated.code == "sv"


async def test_execute_sync_requires_the_permission(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    login(visitor)
    interactor = await dishka_request.get(ExecuteCosplaySync)

    with pytest.raises(AccessDenied):
        await interactor()


async def test_system_user_is_granted_sync_run(dishka_request: AsyncContainer) -> None:
    perm_gateway = await dishka_request.get(UserPermissionGateway)

    granted = await perm_gateway.get_by_permission(
        user_id=SYSTEM_USER_ID, permission=Permission.SYNC_RUN
    )

    assert granted is not None
