from collections.abc import Callable
from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.commands.notifications import CancelMailingCommand
from fanfan.application.interactors.notifications.cancel_mailing import (
    CancelMailing,
    CancelMailingInput,
)
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.notifications import (
    MailingAlreadyCancelled,
    MailingNotCancellable,
    MailingNotFound,
)
from fanfan.core.models.mailing import Mailing
from fanfan.core.models.user import User
from fanfan.core.vo.mailing import MailingId, MailingStatus
from tests.integration.conftest import JobsReader, as_jobs, make_broadcaster

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_cancel_mailing_marks_cancelled_and_enqueues_command(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    jobs: JobsReader,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(CancelMailing)
    mailing_gateway = await dishka_request.get(MailingGateway)
    broadcaster = await make_broadcaster(dishka_request, uow)
    login(broadcaster)

    mailing = Mailing.create(by_user_id=broadcaster.id)
    await mailing_gateway.add(mailing)
    await uow.commit()

    await interactor(CancelMailingInput(mailing_id=mailing.id))

    stored = await mailing_gateway.read_mailing(mailing.id)
    assert stored is not None
    # Flipped synchronously so ensure_active() rejects in-flight sends at once.
    assert stored.status is MailingStatus.CANCELLED
    # The command drives the consumer that deletes the undelivered notifications.
    assert await jobs() == as_jobs(CancelMailingCommand(mailing_id=mailing.id))


async def test_cancel_mailing_twice_raises_already_cancelled(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(CancelMailing)
    mailing_gateway = await dishka_request.get(MailingGateway)
    broadcaster = await make_broadcaster(dishka_request, uow)
    login(broadcaster)

    mailing = Mailing.create(by_user_id=broadcaster.id)
    await mailing_gateway.add(mailing)
    await uow.commit()

    await interactor(CancelMailingInput(mailing_id=mailing.id))
    with pytest.raises(MailingAlreadyCancelled):
        await interactor(CancelMailingInput(mailing_id=mailing.id))
    await uow.rollback()


async def test_cancel_finished_mailing_raises_not_cancellable(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(CancelMailing)
    mailing_gateway = await dishka_request.get(MailingGateway)
    broadcaster = await make_broadcaster(dishka_request, uow)
    login(broadcaster)

    mailing = Mailing.create(by_user_id=broadcaster.id)
    mailing.status = MailingStatus.FINISHED
    await mailing_gateway.add(mailing)
    await uow.commit()

    with pytest.raises(MailingNotCancellable):
        await interactor(CancelMailingInput(mailing_id=mailing.id))
    await uow.rollback()


async def test_cancel_missing_mailing_raises_not_found(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(CancelMailing)
    broadcaster = await make_broadcaster(dishka_request, uow)
    login(broadcaster)

    with pytest.raises(MailingNotFound):
        await interactor(CancelMailingInput(mailing_id=MailingId(uuid7())))
    await uow.rollback()


async def test_cancel_mailing_without_permission_raises_access_denied(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(CancelMailing)
    mailing_gateway = await dishka_request.get(MailingGateway)
    mailing = Mailing.create(by_user_id=visitor.id)
    await mailing_gateway.add(mailing)
    await uow.commit()

    login(visitor)
    with pytest.raises(AccessDenied):
        await interactor(CancelMailingInput(mailing_id=mailing.id))
    await uow.rollback()
