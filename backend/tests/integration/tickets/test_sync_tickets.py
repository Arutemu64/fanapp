import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.tickets.sync_tickets import (
    COMMIT_BATCH_SIZE,
    SyncTickets,
)
from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.sources.tickets import ExternalTicket
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.ticket import Ticket
from fanfan.core.vo.ticket import generate_ticket_id
from fanfan.core.vo.user import UserRole
from tests.fakes.tickets_source import FakeTicketsSource

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


def _external(
    external_id: str,
    barcode: str,
    role: UserRole = UserRole.VISITOR,
) -> ExternalTicket:
    return ExternalTicket(external_id=external_id, barcode=barcode, role=role)


async def test_sync_tickets_imports_new_tickets(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(SyncTickets)
    source = await dishka_request.get(FakeTicketsSource)
    ticket_gateway = await dishka_request.get(TicketGateway)

    source.tickets = [
        _external("ext-1", "barcode-1", UserRole.VISITOR),
        _external("ext-2", "barcode-2", UserRole.PARTICIPANT),
        _external("ext-3", "barcode-3", UserRole.VISITOR),
    ]

    result = await interactor()

    assert result.new_tickets_count == 3
    assert result.removed_tickets_count == 0

    for external in source.tickets:
        saved = await ticket_gateway.get_by_ticketscloud_ticket_id(external.external_id)
        assert saved is not None
        assert saved.barcode == external.barcode
        assert saved.role == external.role
        # Synced tickets are unissued and unlinked until a user claims them.
        assert saved.used_by_user_id is None
        assert saved.issued_by_user_id is None


async def test_sync_tickets_is_idempotent_and_does_not_overwrite_existing(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(SyncTickets)
    source = await dishka_request.get(FakeTicketsSource)
    ticket_gateway = await dishka_request.get(TicketGateway)

    # A ticket already imported in a previous sync, with its own barcode/role.
    existing = Ticket(
        id=generate_ticket_id(),
        barcode="original-barcode",
        role=UserRole.PARTICIPANT,
        used_by_user_id=None,
        issued_by_user_id=None,
        ticketscloud_ticket_id="ext-1",
    )
    await ticket_gateway.add(existing)
    await uow.commit()

    # The source re-yields ext-1 (now with different data) plus a brand new
    # ticket. Import keys off the external id, so ext-1 must be left untouched
    # and only ext-2 counts as new.
    source.tickets = [
        _external("ext-1", "changed-barcode", UserRole.VISITOR),
        _external("ext-2", "barcode-2", UserRole.VISITOR),
    ]

    result = await interactor()

    assert result.new_tickets_count == 1

    # The existing ticket is not overwritten by the re-synced payload.
    saved_existing = await ticket_gateway.get_by_ticketscloud_ticket_id("ext-1")
    assert saved_existing is not None
    assert saved_existing.id == existing.id
    assert saved_existing.barcode == "original-barcode"
    assert saved_existing.role == UserRole.PARTICIPANT

    saved_new = await ticket_gateway.get_by_ticketscloud_ticket_id("ext-2")
    assert saved_new is not None
    assert saved_new.barcode == "barcode-2"


async def test_sync_tickets_with_empty_source_imports_nothing(
    dishka_request: AsyncContainer,
):
    interactor = await dishka_request.get(SyncTickets)
    source = await dishka_request.get(FakeTicketsSource)

    source.tickets = []

    result = await interactor()

    assert result.new_tickets_count == 0
    assert result.removed_tickets_count == 0


async def test_sync_tickets_commits_in_batches_persisting_all_tickets(
    dishka_request: AsyncContainer,
):
    # Cross the batch-commit boundary so the mid-loop commit path runs and we
    # verify no ticket is dropped when the run spans multiple transactions.
    total = COMMIT_BATCH_SIZE + 5
    interactor = await dishka_request.get(SyncTickets)
    source = await dishka_request.get(FakeTicketsSource)
    ticket_gateway = await dishka_request.get(TicketGateway)

    source.tickets = [_external(f"ext-{i}", f"barcode-{i}") for i in range(total)]

    result = await interactor()

    assert result.new_tickets_count == total
    # Spot-check that tickets on both sides of the batch boundary persisted.
    for i in (0, COMMIT_BATCH_SIZE - 1, COMMIT_BATCH_SIZE, total - 1):
        saved = await ticket_gateway.get_by_ticketscloud_ticket_id(f"ext-{i}")
        assert saved is not None
        assert saved.barcode == f"barcode-{i}"
