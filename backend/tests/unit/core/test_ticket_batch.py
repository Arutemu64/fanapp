from uuid import uuid7

import pytest

from fanfan.core.models.ticket_batch import TicketBatch
from fanfan.core.vo.ticket import TicketBatchId
from fanfan.core.vo.user import UserId, UserRole

pytestmark = pytest.mark.unit

ISSUER = UserId(uuid7())


def _batch(amount: int = 5) -> TicketBatch:
    return TicketBatch.issue(
        batch_id=TicketBatchId(uuid7()),
        role=UserRole.VOLUNTEER,
        amount=amount,
        issued_by_user_id=ISSUER,
    )


def test_issue_builds_unique_tickets_of_the_batch() -> None:
    batch = _batch(amount=5)

    assert len(batch.tickets) == 5
    assert len(set(batch.barcodes)) == 5
    for ticket in batch.tickets:
        assert ticket.batch_id == batch.id
        assert ticket.role == UserRole.VOLUNTEER
        assert ticket.issued_by_user_id == ISSUER


def test_redraw_barcodes_replaces_every_barcode() -> None:
    batch = _batch(amount=3)
    before = set(batch.barcodes)

    batch.redraw_barcodes()

    assert len(set(batch.barcodes)) == 3
    assert before.isdisjoint(batch.barcodes)


def test_same_request_matches_issuer_role_and_amount() -> None:
    batch = _batch(amount=5)

    assert batch.is_same_request(by_user_id=ISSUER, role=UserRole.VOLUNTEER, amount=5)
    assert not batch.is_same_request(
        by_user_id=ISSUER, role=UserRole.VOLUNTEER, amount=4
    )
    assert not batch.is_same_request(
        by_user_id=ISSUER, role=UserRole.ORGANIZER, amount=5
    )
    assert not batch.is_same_request(
        by_user_id=UserId(uuid7()), role=UserRole.VOLUNTEER, amount=5
    )
