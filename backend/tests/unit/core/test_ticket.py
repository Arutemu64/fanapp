from datetime import UTC, datetime, timedelta
from uuid import uuid7

import pytest

from fanfan.core.exceptions.tickets import TicketAlreadyUsed, TicketRevoked
from fanfan.core.models.ticket import Ticket
from fanfan.core.vo.ticket import (
    generate_ticket_barcode,
    generate_ticket_id,
    normalize_ticket_barcode,
)
from fanfan.core.vo.user import UserId, UserRole

pytestmark = pytest.mark.unit


def _ticket(used_by: UserId | None = None) -> Ticket:
    return Ticket(
        id=generate_ticket_id(),
        barcode="TICKET-1",
        role=UserRole.VISITOR,
        used_by_user_id=used_by,
        issued_by_user_id=None,
        ticketscloud_ticket_id=None,
    )


def test_fresh_ticket_is_not_used() -> None:
    ticket = _ticket()

    assert ticket.is_used is False


def test_set_as_used_marks_ticket_for_user() -> None:
    ticket = _ticket()
    user_id = UserId(uuid7())

    ticket.set_as_used(user_id)

    assert ticket.is_used is True
    assert ticket.is_used_by(user_id) is True
    assert ticket.is_used_by(UserId(uuid7())) is False


def test_set_as_used_twice_raises() -> None:
    ticket = _ticket(used_by=UserId(uuid7()))

    with pytest.raises(TicketAlreadyUsed):
        ticket.set_as_used(UserId(uuid7()))


def test_revoked_ticket_cannot_be_linked() -> None:
    ticket = _ticket()
    ticket.revoke(datetime.now(UTC))

    with pytest.raises(TicketRevoked):
        ticket.set_as_used(UserId(uuid7()))


def test_revoking_linked_ticket_keeps_its_user() -> None:
    user_id = UserId(uuid7())
    ticket = _ticket(used_by=user_id)

    ticket.revoke(datetime.now(UTC))

    assert ticket.is_revoked is True
    assert ticket.is_used_by(user_id) is True


def test_revoke_keeps_first_revocation_time() -> None:
    first = datetime.now(UTC)
    ticket = _ticket()

    ticket.revoke(first)
    ticket.revoke(first + timedelta(hours=1))

    assert ticket.revoked_at == first


@pytest.mark.parametrize(
    ("typed", "stored"),
    [
        ("FAN-7K4Q9M", "FAN-7K4Q9M"),
        ("fan-7k4q9m", "FAN-7K4Q9M"),
        ("  Fan-7k4Q9m ", "FAN-7K4Q9M"),
        ("fan-o1il2m", "FAN-01112M"),
    ],
)
def test_normalize_folds_org_barcode_case_and_confusables(
    typed: str, stored: str
) -> None:
    assert normalize_ticket_barcode(typed) == stored


def test_normalize_keeps_generated_barcode_intact() -> None:
    barcode = generate_ticket_barcode()

    assert normalize_ticket_barcode(barcode.lower()) == barcode


def test_normalize_leaves_vendor_barcode_spelling_alone() -> None:
    assert normalize_ticket_barcode(" 0042abC ") == "0042abC"
