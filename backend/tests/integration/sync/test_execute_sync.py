from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

import pytest
from dishka import AsyncContainer
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import SyncRunORM
from fanfan.application.interactors.sync.execute_cosplay_sync import ExecuteCosplaySync
from fanfan.application.ports.gateways import UserPermissionGateway
from fanfan.application.ports.gateways.sync_runs import SyncRunGateway
from fanfan.application.ports.sources.cosplay import ExternalNomination
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.sync_run_tracker import STALE_RUN_TIMEOUT
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.sync_run import SyncRun
from fanfan.core.models.user import User
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
):
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
):
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


async def test_unattended_run_skips_quietly_when_one_is_active(
    dishka_request: AsyncContainer,
    sync_operator: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
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
):
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


async def test_vendor_failure_is_recorded_not_raised(
    dishka_request: AsyncContainer,
    sync_operator: User,
    login: Callable[[User], None],
):
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


async def test_execute_sync_requires_the_permission(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    # The check on the unattended path is real, not decorative.
    login(visitor)
    interactor = await dishka_request.get(ExecuteCosplaySync)

    with pytest.raises(AccessDenied):
        await interactor()


async def test_system_user_is_granted_sync_run(dishka_request: AsyncContainer):
    # Guards the grant in the sync:run migration. Cron and CLI syncs
    # authenticate as this seeded user and go through the same permission check,
    # so losing that user_permissions row silently stops all unattended syncing
    # — the failure is a recorded AccessDenied, not a crash anyone would notice.
    perm_gateway = await dishka_request.get(UserPermissionGateway)

    granted = await perm_gateway.get_by_permission(
        user_id=SYSTEM_USER_ID, permission=Permission.SYNC_RUN
    )

    assert granted is not None
