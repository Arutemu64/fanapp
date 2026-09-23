from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

import pytest
from dishka import AsyncContainer
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from fanfan.adapters.db.models import SyncRunORM
from fanfan.adapters.db.run_lease import PostgresRunLease
from fanfan.application.interactors.sync.execute_cosplay_sync import ExecuteCosplaySync
from fanfan.application.ports.gateways import UserPermissionGateway
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.gateways.sync_runs import SyncRunGateway
from fanfan.application.ports.sources.cosplay import ExternalNomination
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.sync_run_tracker import (
    STALE_RUN_TIMEOUT,
    sync_lease_key,
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

# Seeded by the initial-data migration; the actor for CLI/scheduler/NATS work.
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
    # The cron/CLI path: no run_id, so the interactor creates its own row. This
    # is the whole point of the Execute*Sync layer — without it, scheduled syncs
    # would leave no trace and "last synced" would only show manual runs.
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
    # The manual path: RequestSync already created the row, so the consumer must
    # move that one along rather than inserting a second.
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
    # The SyncRequested consumer redelivers its trigger after an error, or when a
    # long sync outlasts AckWait. A run that already moved past PENDING must not
    # start again, or one request would hit the vendor twice.
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
    # A worker that died after committing RUNNING never acked its trigger, so
    # NATS redelivers it. The consumer heartbeats while a sync is alive, so that
    # redelivery means the run was interrupted, and it must be picked up again
    # rather than acked away and left for reap_stale.
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
    # A worker that missed its NATS heartbeats is still running, and its trigger
    # got redelivered. Redelivery alone cannot tell it from a dead worker; the
    # lease it holds can. The redelivered trigger must back off (raise, so the
    # consumer retries later) instead of running the same sync alongside it.
    login(sync_operator)
    source = await dishka_request.get(FakeCosplaySource)
    source.nominations = [ExternalNomination(external_id=1, code="c1", title="Косплей")]
    gateway = await dishka_request.get(SyncRunGateway)
    running = SyncRun.create(source=SyncSource.COSPLAY2, by_user_id=sync_operator.id)
    running.mark_running(datetime.now(UTC))
    await gateway.add(running)
    await uow.commit()
    live_worker = PostgresRunLease(await dishka_request.get(AsyncEngine))
    assert await live_worker.try_acquire(sync_lease_key(SyncSource.COSPLAY2))

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
    # A scheduled tick colliding with a manual run must not raise: the scheduler
    # would report it to Sentry on every overlap.
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
    # A full sweep can outlast STALE_RUN_TIMEOUT. Age alone must not get it
    # reaped while its worker still holds the lease, or the next tick would
    # start a second sweep of the same source alongside it.
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
    live_worker = PostgresRunLease(await dishka_request.get(AsyncEngine))
    assert await live_worker.try_acquire(sync_lease_key(SyncSource.COSPLAY2))

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
    # Re-raising would make the NATS consumer redeliver and retry forever
    # against a vendor that is simply down.
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
    # A vendor error that raises *before* the DB is touched (the test above) is
    # the easy case. This one fails during a flush: two nominations sharing a
    # code violate uq_nominations_code, which poisons the session. fail() must
    # roll that back before writing the FAILED row — otherwise persisting it
    # raises PendingRollbackError and the run stays stuck in RUNNING ("syncing").
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
    # Cosplay2 retires a nomination and issues a new one (a new cosplay2_id) that
    # reuses the old code. Because stale nominations are pruned before the upsert
    # loop, the old row is deleted first and frees its code for the newcomer —
    # rather than the insert colliding on uq_nominations_code.
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
    # The check on the unattended path is real, not decorative.
    login(visitor)
    interactor = await dishka_request.get(ExecuteCosplaySync)

    with pytest.raises(AccessDenied):
        await interactor()


async def test_system_user_is_granted_sync_run(dishka_request: AsyncContainer) -> None:
    # Guards the grant in the sync:run migration. Cron and CLI syncs
    # authenticate as this seeded user and go through the same permission check,
    # so losing that user_permissions row silently stops all unattended syncing
    # — the failure is a recorded AccessDenied, not a crash anyone would notice.
    perm_gateway = await dishka_request.get(UserPermissionGateway)

    granted = await perm_gateway.get_by_permission(
        user_id=SYSTEM_USER_ID, permission=Permission.SYNC_RUN
    )

    assert granted is not None
