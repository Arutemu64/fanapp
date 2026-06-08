from uuid import uuid7

import pytest

from fanfan.core.exceptions.tickets import TicketAlreadyUsed
from fanfan.core.models.ticket import Ticket
from fanfan.core.vo.ticket import generate_ticket_id
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


def test_fresh_ticket_is_not_used():
    ticket = _ticket()

    assert ticket.is_used is False


def test_set_as_used_marks_ticket_for_user():
    ticket = _ticket()
    user_id = UserId(uuid7())

    ticket.set_as_used(user_id)

    assert ticket.is_used is True
    assert ticket.is_used_by(user_id) is True
    assert ticket.is_used_by(UserId(uuid7())) is False


def test_set_as_used_twice_raises():
    ticket = _ticket(used_by=UserId(uuid7()))

    with pytest.raises(TicketAlreadyUsed):
        ticket.set_as_used(UserId(uuid7()))


def test_unlink_returns_previous_user_and_clears_it():
    user_id = UserId(uuid7())
    ticket = _ticket(used_by=user_id)

    unlinked = ticket.unlink()

    assert unlinked == user_id
    assert ticket.is_used is False


def test_unlink_unused_ticket_returns_none():
    ticket = _ticket()

    assert ticket.unlink() is None
    assert ticket.is_used is False
