import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.tickets.sync_tickets import (
    COMMIT_BATCH_SIZE,
    SyncTickets,
)
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.sources.tickets import (
    ExternalTicket,
    RevokedExternalTicket,
)
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.ticket import Ticket
from fanfan.core.vo.ticket import generate_ticket_id
from fanfan.core.vo.user import UserRole
from tests.fakes.tickets_source import FakeTicketsSource

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]

EVENT_VISITOR = "event-visitor"
EVENT_PARTICIPANT = "event-participant"
EVENT_UNMAPPED = "event-unmapped"


def _external(
    external_id: str,
    barcode: str,
    event_id: str = EVENT_VISITOR,
    order_id: str = "order-1",
) -> ExternalTicket:
    return ExternalTicket(
        order_id=order_id, external_id=external_id, barcode=barcode, event_id=event_id
    )


async def test_sync_tickets_imports_new_tickets(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(SyncTickets)
    source = await dishka_request.get(FakeTicketsSource)
    ticket_gateway = await dishka_request.get(TicketGateway)
    settings_gateway = await dishka_request.get(AppSettingsGateway)

    settings = await settings_gateway.get_for_update()
    settings.set_tcloud_event_roles(
        {EVENT_VISITOR: UserRole.VISITOR, EVENT_PARTICIPANT: UserRole.PARTICIPANT}
    )
    await settings_gateway.save(settings)
    await uow.commit()

    source.tickets = [
        _external("ext-1", "barcode-1", EVENT_VISITOR),
        _external("ext-2", "barcode-2", EVENT_PARTICIPANT),
        _external("ext-3", "barcode-3", EVENT_UNMAPPED),
    ]
    expected_roles = {
        "barcode-1": UserRole.VISITOR,
        "barcode-2": UserRole.PARTICIPANT,
        "barcode-3": UserRole.VISITOR,
    }

    result = await interactor()

    assert result.new_tickets_count == 3
    assert result.revoked_tickets_count == 0

    for external in source.tickets:
        saved = await ticket_gateway.get_by_barcode(external.barcode)
        assert saved is not None
        assert saved.barcode == external.barcode
        assert saved.role == expected_roles[external.barcode]
        assert saved.used_by_user_id is None
        assert saved.issued_by_user_id is None


async def test_sync_tickets_is_idempotent_and_does_not_overwrite_existing(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(SyncTickets)
    source = await dishka_request.get(FakeTicketsSource)
    ticket_gateway = await dishka_request.get(TicketGateway)

    existing = Ticket(
        id=generate_ticket_id(),
        barcode="original-barcode",
        role=UserRole.PARTICIPANT,
        used_by_user_id=None,
        issued_by_user_id=None,
        ticketscloud_ticket_id="ext-1",
        ticketscloud_order_id="order-1",
    )
    await ticket_gateway.add(existing)
    await uow.commit()

    source.tickets = [
        _external("ext-1", "changed-barcode"),
        _external("ext-2", "barcode-2"),
    ]

    result = await interactor()

    assert result.new_tickets_count == 1

    saved_existing = await ticket_gateway.get_by_ticketscloud_sale(
        order_id="order-1", ticket_id="ext-1"
    )
    assert saved_existing is not None
    assert saved_existing.id == existing.id
    assert saved_existing.barcode == "original-barcode"
    assert saved_existing.role == UserRole.PARTICIPANT

    saved_new = await ticket_gateway.get_by_ticketscloud_sale(
        order_id="order-1", ticket_id="ext-2"
    )
    assert saved_new is not None
    assert saved_new.barcode == "barcode-2"


async def test_sync_tickets_with_empty_source_imports_nothing(
    dishka_request: AsyncContainer,
) -> None:
    interactor = await dishka_request.get(SyncTickets)
    source = await dishka_request.get(FakeTicketsSource)

    source.tickets = []

    result = await interactor()

    assert result.new_tickets_count == 0
    assert result.revoked_tickets_count == 0


async def test_sync_tickets_commits_in_batches_persisting_all_tickets(
    dishka_request: AsyncContainer,
) -> None:
    total = COMMIT_BATCH_SIZE + 5
    interactor = await dishka_request.get(SyncTickets)
    source = await dishka_request.get(FakeTicketsSource)
    ticket_gateway = await dishka_request.get(TicketGateway)

    source.tickets = [_external(f"ext-{i}", f"barcode-{i}") for i in range(total)]

    result = await interactor()

    assert result.new_tickets_count == total
    for i in (0, COMMIT_BATCH_SIZE - 1, COMMIT_BATCH_SIZE, total - 1):
        saved = await ticket_gateway.get_by_barcode(f"barcode-{i}")
        assert saved is not None
        assert saved.barcode == f"barcode-{i}"


async def test_sync_tickets_imports_resale_of_refunded_ticket_id(
    dishka_request: AsyncContainer,
) -> None:
    interactor = await dishka_request.get(SyncTickets)
    source = await dishka_request.get(FakeTicketsSource)
    ticket_gateway = await dishka_request.get(TicketGateway)

    source.tickets = [
        _external("ext-1", "first-sale", order_id="order-1"),
        _external("ext-1", "resale", order_id="order-2"),
    ]
    source.revoked = [RevokedExternalTicket(order_id="order-1", external_id="ext-1")]

    result = await interactor()

    assert result.new_tickets_count == 1
    assert result.revoked_tickets_count == 1
    first_sale = await ticket_gateway.get_by_barcode("first-sale")
    resale = await ticket_gateway.get_by_barcode("resale")
    assert first_sale is not None
    assert first_sale.is_revoked
    assert resale is not None
    assert not resale.is_revoked


async def test_sync_tickets_backfills_order_id_and_revokes_legacy_ticket(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(SyncTickets)
    source = await dishka_request.get(FakeTicketsSource)
    ticket_gateway = await dishka_request.get(TicketGateway)

    legacy = Ticket(
        id=generate_ticket_id(),
        barcode="legacy-barcode",
        role=UserRole.VISITOR,
        used_by_user_id=None,
        issued_by_user_id=None,
        ticketscloud_ticket_id="ext-1",
    )
    await ticket_gateway.add(legacy)
    await uow.commit()

    source.tickets = [_external("ext-1", "legacy-barcode", order_id="order-1")]
    source.revoked = [RevokedExternalTicket(order_id="order-1", external_id="ext-1")]

    result = await interactor()

    assert result.new_tickets_count == 0
    assert result.revoked_tickets_count == 1
    saved = await ticket_gateway.get_by_barcode("legacy-barcode")
    assert saved is not None
    assert saved.id == legacy.id
    assert saved.ticketscloud_order_id == "order-1"
    assert saved.is_revoked


async def test_sync_tickets_revokes_legacy_ticket_missing_from_sweep(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(SyncTickets)
    source = await dishka_request.get(FakeTicketsSource)
    ticket_gateway = await dishka_request.get(TicketGateway)

    legacy = Ticket(
        id=generate_ticket_id(),
        barcode="legacy-barcode",
        role=UserRole.VISITOR,
        used_by_user_id=None,
        issued_by_user_id=None,
        ticketscloud_ticket_id="ext-1",
    )
    await ticket_gateway.add(legacy)
    await uow.commit()

    source.revoked = [RevokedExternalTicket(order_id="order-1", external_id="ext-1")]

    result = await interactor()

    assert result.revoked_tickets_count == 1
    saved = await ticket_gateway.get_by_barcode("legacy-barcode")
    assert saved is not None
    assert saved.is_revoked
